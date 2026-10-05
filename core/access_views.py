"""Telas de acesso: lista de usuários, usuário numa página só e grupos de acesso.

Tudo aqui é a camada amigável sobre o motor que já existe (ver `acessos/screens.py` e
`acessos/screen_services.py`): grupo = perfil de acesso, equipe = participação em setor, "vale
para" = escopo, ajuste individual = concessão direta. A matriz de ações (`/permissoes/`) e os
acessos avançados de uma pessoa (`/usuarios/<id>/acessos/`) continuam existindo para o ajuste fino.
"""

import re

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from accounts.invitations import send_invitation
from accounts.models import UserSector
from acessos import catalog, screens
from acessos.models import Profile as AccessProfile
from acessos.screen_services import (
    SCOPE_CHOICES,
    SCOPE_CUSTOM,
    SCOPE_ORG,
    GroupError,
    GroupService,
    UserAccessService,
    advanced_summary,
    default_scope_kind,
    invitation_pending,
    keys_by_profile,
    profile_levels,
)
from acessos.services import AccessService, AuthorizationService
from audit.models import AuditLog
from audit.services import AuditService

from .mixins import ActionRequiredMixin, OrganizationRequiredMixin
from .models import Sector
from .services import CadastroError

User = get_user_model()


# ---------------------------------------------------------------------------
# Peças compartilhadas
# ---------------------------------------------------------------------------


def screen_sections(levels, floor=None):
    """Seções e linhas de telas prontas para o template.

    `floor` (níveis do grupo) só existe na tela da pessoa: um nível abaixo do grupo fica
    desabilitado, porque o motor não tem "negar" — para tirar uma tela, troque de grupo.
    """
    sections = []
    for key, name, items in screens.sections():
        rows = []
        for screen in items:
            level = levels.get(screen.key, screens.NONE)
            base = floor.get(screen.key, screens.NONE) if floor is not None else screens.NONE
            rows.append(
                {
                    "screen": screen,
                    "level": level,
                    "floor": base,
                    "individual": floor is not None and screens.rank(level) > screens.rank(base),
                    "options": [
                        {
                            "value": value,
                            "label": screens.LEVEL_LABELS[value],
                            "checked": value == level,
                            "disabled": screens.rank(value) < screens.rank(base),
                        }
                        for value in screen.levels
                    ],
                }
            )
        sections.append({"key": key, "name": name, "rows": rows})
    return sections


def levels_from_post(post, fallback):
    """Níveis enviados pelo formulário (`screen_<tela>`); o que faltar mantém o valor anterior."""
    levels = {}
    for screen in screens.SCREENS:
        raw = post.get(f"screen_{screen.key}")
        levels[screen.key] = screens.normalize_level(screen, raw) if raw else fallback.get(screen.key, screens.NONE)
    return levels


def group_badge_classes(groups):
    """Cor estável de cada grupo na lista: um ciclo curto, para diferenciar sem inventar semântica."""
    palette = ["blue", "green", "slate"]
    return {group.pk: palette[index % len(palette)] for index, group in enumerate(groups)}


# ---------------------------------------------------------------------------
# Lista de usuários
# ---------------------------------------------------------------------------

SITUATIONS = [
    ("ativos", "Ativos"),
    ("todos", "Todos"),
    ("convite", "Convite pendente"),
    ("inativos", "Inativos"),
]


class UserListView(OrganizationRequiredMixin, ActionRequiredMixin, TemplateView):
    template_name = "core/user_list.html"
    required_action = catalog.USUARIO_VISUALIZAR

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        organization = self.organization

        search = request.GET.get("q", "").strip()
        group_id = request.GET.get("grupo", "")
        situation = request.GET.get("situacao", "ativos")
        if situation not in dict(SITUATIONS):
            situation = "ativos"
        team_id = request.GET.get("equipe", "")
        only_full = request.GET.get("acesso") == "total"

        base = User.objects.filter(profile__organization=organization)
        users = base
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        if situation == "ativos":
            users = users.filter(is_active=True)
        elif situation == "inativos":
            users = users.filter(is_active=False)
        elif situation == "convite":
            users = users.filter(is_active=True, last_login__isnull=True, password__startswith="!")
        if group_id.isdigit():
            users = users.filter(access_profiles__profile_id=int(group_id), access_profiles__is_active=True)
        if team_id.isdigit():
            users = users.filter(
                sector_memberships__sector_id=int(team_id), sector_memberships__removed_at__isnull=True
            )

        users = (
            users.select_related("profile")
            .prefetch_related(
                Prefetch(
                    "sector_memberships",
                    queryset=UserSector.objects.filter(removed_at__isnull=True).select_related("sector"),
                    to_attr="active_memberships",
                )
            )
            .order_by("first_name", "username")
            .distinct()
        )
        users = list(users)
        overview = UserAccessService.overview(users)

        # O aviso olha a organização toda (não o filtro da tela): quem está como Administrador.
        everyone = list(base.filter(is_active=True))
        full_ids = {
            pk for pk, info in UserAccessService.overview(everyone).items() if info["full"]
        }

        if only_full:
            users = [user for user in users if user.pk in full_ids]

        groups = list(GroupService.groups(organization))
        colors = group_badge_classes(groups)
        rows = []
        for user in users:
            info = overview[user.pk]
            teams = [m.sector for m in user.active_memberships if m.sector.is_active]
            rows.append(
                {
                    "user": user,
                    "teams": teams,
                    "groups": [(group, colors.get(group.pk, "slate")) for group in info["groups"]],
                    "superuser": user.is_superuser,
                    "screens": info["screens"],
                    "all_screens": info["full"],
                    "individual": info["individual"],
                    "full": info["full"],
                    "state": self._state(user),
                    "initials": self._initials(user),
                }
            )

        teams = list(Sector.objects.filter(organization=organization, is_active=True))
        params = {"q": search, "grupo": group_id, "situacao": situation}
        context.update(
            {
                "rows": rows,
                "search": search,
                "groups": groups,
                "group_id": group_id,
                "situations": SITUATIONS,
                "situation": situation,
                "team_chips": self._team_chips(teams, team_id, params),
                "team_id": team_id,
                "full_count": len(full_ids),
                "only_full": only_full,
                "can_create": AuthorizationService.can(request.user, catalog.USUARIO_CRIAR),
                "can_edit": AuthorizationService.can(request.user, catalog.USUARIO_EDITAR),
                "can_groups": AuthorizationService.can(request.user, catalog.SEGURANCA_GERIR_PERFIS),
                "total": len(rows),
            }
        )
        return context

    @staticmethod
    def _state(user):
        if not user.is_active:
            return ("inactive", "Inativo")
        if invitation_pending(user):
            return ("pending", "Convite pendente")
        return ("active", "Ativo")

    @staticmethod
    def _initials(user):
        name = (user.get_full_name() or user.get_username()).split()
        letters = "".join(part[0] for part in name[:2])
        return (letters or user.get_username()[:2]).upper()

    @staticmethod
    def _team_chips(teams, active_id, params):
        from urllib.parse import urlencode

        def link(team_id):
            query = {key: value for key, value in params.items() if value}
            if team_id:
                query["equipe"] = team_id
            return f"{reverse('user-list')}?{urlencode(query)}" if query else reverse("user-list")

        chips = [{"label": "Todas as equipes", "url": link(""), "active": not active_id}]
        chips += [
            {"label": team.name, "url": link(team.pk), "active": str(team.pk) == str(active_id)}
            for team in teams
        ]
        return chips


# ---------------------------------------------------------------------------
# Usuário (cadastro e edição numa página só)
# ---------------------------------------------------------------------------

FIRST_ACCESS_CHOICES = [
    ("invite", "Enviar convite por e-mail"),
    ("password", "Definir senha provisória"),
]


class UserEditorForm(forms.Form):
    """Dados da pessoa e primeiro acesso. Equipes, grupo e telas são lidos direto do POST."""

    first_name = forms.CharField(label="Nome completo", max_length=150)
    email = forms.EmailField(label="E-mail")
    username = forms.CharField(label="Usuário (login)", max_length=150, required=False)
    phone = forms.CharField(label="Telefone", max_length=20, required=False)
    first_access = forms.ChoiceField(
        choices=[("keep", "Não alterar")] + FIRST_ACCESS_CHOICES, required=False, initial="invite"
    )
    password1 = forms.CharField(
        label="Senha provisória", required=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        label="Repita a senha", required=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    is_active = forms.BooleanField(label="Permitir que esta pessoa entre na LPS", required=False)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields["first_name"].widget.attrs["placeholder"] = "Ex.: Maria Oliveira"
        self.fields["email"].widget.attrs["placeholder"] = "nome@empresa.com"
        self.fields["username"].widget.attrs["placeholder"] = "Gerado a partir do e-mail"
        self.fields["phone"].widget.attrs["placeholder"] = "(00) 00000-0000"
        if instance is not None and not self.is_bound:
            self.initial.update(
                {
                    "first_name": instance.first_name,
                    "email": instance.email,
                    "username": instance.username,
                    "phone": instance.profile.phone,
                    "is_active": instance.is_active,
                    "first_access": "keep",
                }
            )
        elif instance is None and not self.is_bound:
            self.initial.update({"is_active": True, "first_access": "invite"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if self.instance is not None and email == (self.instance.email or "").strip().lower():
            return email  # quem já tinha esse e-mail (inclusive repetido de antes) pode editar o resto
        # O login é por e-mail: dois cadastros com o mesmo e-mail impedem as duas pessoas de entrar.
        queryset = User.objects.filter(email__iexact=email)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Já existe uma pessoa com este e-mail.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            return ""
        queryset = User.objects.filter(username__iexact=username)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Já existe um usuário com este nome de usuário.")
        return username

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("first_access") or ("keep" if self.instance is not None else "invite")
        if self.instance is None and mode == "keep":
            mode = "invite"
        cleaned["first_access"] = mode

        if mode == "password":
            password1, password2 = cleaned.get("password1"), cleaned.get("password2")
            if not password1:
                self.add_error("password1", "Defina a senha provisória.")
            elif password1 != password2:
                self.add_error("password2", "As senhas não coincidem.")
            else:
                try:
                    password_validation.validate_password(password1, user=self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned


def _unique_username(email):
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower()) or "usuario"
    candidate, number = base, 1
    while User.objects.filter(username__iexact=candidate).exists():
        number += 1
        candidate = f"{base}{number}"
    return candidate[:150]


class UserEditorView(OrganizationRequiredMixin, ActionRequiredMixin, View):
    """Quem é, em qual equipe trabalha e o que pode acessar — numa tela só."""

    template_name = "core/user_editor.html"

    @property
    def required_action(self):
        return catalog.USUARIO_EDITAR if self.kwargs.get("pk") else catalog.USUARIO_CRIAR

    # -- carga ---------------------------------------------------------

    def get_instance(self):
        pk = self.kwargs.get("pk")
        if pk is None:
            return None
        return get_object_or_404(User.objects.select_related("profile"), pk=pk, profile__organization=self.organization)

    def can_manage_access(self):
        return AuthorizationService.can(self.request.user, catalog.SEGURANCA_GERIR_AUTORIZACOES)

    def can_set_superuser(self):
        return AuthorizationService.is_platform_admin(self.request.user)

    def groups(self):
        return list(GroupService.groups(self.organization))

    def initial_selection(self, instance, groups):
        """Seleção de equipes, grupo, "vale para" e níveis a partir do que já existe."""
        if instance is None:
            default = next((g for g in groups if g.name.lower() == "colaborador"), groups[0] if groups else None)
            levels = profile_levels(default) if default else {s.key: screens.NONE for s in screens.SCREENS}
            return {
                "teams": [],
                "roles": {},
                "main": None,
                "group": default.pk if default else None,
                "scope": default_scope_kind(levels),
                "levels": levels,
                "state": None,
                "complex": False,
            }

        memberships = UserSector.objects.filter(user=instance, removed_at__isnull=True)
        state = UserAccessService.state(instance)
        return {
            "teams": [m.sector_id for m in memberships],
            "roles": {m.sector_id: m.role for m in memberships},
            "main": instance.profile.main_sector_id,
            "group": state["group"].pk if state["group"] else None,
            "scope": state["scope_kind"] or SCOPE_ORG,
            "levels": state["levels"],
            "state": state,
            "complex": state["complex"],
        }

    def selection_from_post(self, instance, groups, initial):
        post = self.request.POST
        team_ids = {s.pk for s in Sector.objects.filter(organization=self.organization, is_active=True)}
        teams = [int(v) for v in post.getlist("teams") if v.isdigit() and int(v) in team_ids]
        roles = {
            pk: (UserSector.Role.GESTOR if post.get(f"role_{pk}") == UserSector.Role.GESTOR else UserSector.Role.MEMBRO)
            for pk in teams
        }
        main = int(post["main_sector"]) if post.get("main_sector", "").isdigit() else None
        if main not in teams:
            main = teams[0] if teams else None

        group_id = int(post["group"]) if post.get("group", "").isdigit() else None
        valid = {g.pk for g in groups}
        group_id = group_id if group_id in valid else None
        # Tela que não veio no envio: com o mesmo grupo de antes, fica como estava (ajustes inclusos);
        # com outro grupo, acompanha o grupo novo — nunca herda o que o grupo anterior dava.
        fallback = initial["levels"]
        if group_id is not None and group_id != initial["group"]:
            fallback = profile_levels(next(g for g in groups if g.pk == group_id))
        scope = post.get("scope") if post.get("scope") in dict(SCOPE_CHOICES) else initial["scope"]
        if initial["scope"] == SCOPE_CUSTOM and post.get("scope") == SCOPE_CUSTOM:
            scope = SCOPE_CUSTOM
        return {
            "teams": teams,
            "roles": roles,
            "main": main,
            "group": group_id,
            "scope": scope,
            "levels": levels_from_post(post, fallback),
            "state": initial["state"],
            "complex": initial["complex"],
        }

    # -- tela ----------------------------------------------------------

    def render(self, form, selection, instance, groups, status=200):
        from django.shortcuts import render

        all_teams = list(Sector.objects.filter(organization=self.organization, is_active=True))
        keys = keys_by_profile([g.pk for g in groups])
        group_levels = {pk: screens.levels_from_actions(found) for pk, found in keys.items()}
        chosen = next((g for g in groups if g.pk == selection["group"]), None)
        floor = group_levels.get(selection["group"]) if chosen else None
        if selection["complex"] and selection["state"]:
            floor = selection["state"]["group_levels"]

        counts_levels = selection["levels"]
        view_only = sum(1 for s in screens.SCREENS if counts_levels[s.key] == screens.VIEW and s.can_edit)
        individual = (
            sum(
                1
                for s in screens.SCREENS
                if floor is not None and screens.rank(counts_levels[s.key]) > screens.rank(floor[s.key])
            )
            if floor is not None
            else 0
        )

        group_cards = []
        for group in groups:
            levels = group_levels[group.pk]
            group_cards.append(
                {
                    "group": group,
                    "levels": levels,
                    "screens": screens.screens_count(levels),
                    "full": levels == screens.full_levels(),
                    "selected": group.pk == selection["group"],
                    "default_scope": default_scope_kind(levels),
                    "advanced": advanced_summary(keys[group.pk])[0],
                }
            )

        context = {
            "form": form,
            "instance": instance,
            "teams": [
                {
                    "sector": team,
                    "selected": team.pk in selection["teams"],
                    "role": selection["roles"].get(team.pk, UserSector.Role.MEMBRO),
                    "main": team.pk == selection["main"],
                }
                for team in all_teams
            ],
            "selection": selection,
            "group_cards": group_cards,
            "sections": screen_sections(selection["levels"], floor=floor),
            "scope_choices": SCOPE_CHOICES
            + ([(SCOPE_CUSTOM, "Personalizado (definido em Acessos avançados)")] if selection["scope"] == SCOPE_CUSTOM else []),
            "can_manage_access": self.can_manage_access(),
            "can_set_superuser": self.can_set_superuser(),
            "is_superuser": (
                self.request.POST.get("is_superuser") == "on"
                if self.request.method == "POST" and self.can_set_superuser()
                else bool(instance and instance.is_superuser)
            ),
            "access_locked": selection["complex"] or not self.can_manage_access(),
            "complex": selection["complex"],
            "assignments": selection["state"]["assignments"] if selection["state"] else [],
            "pending_invite": bool(instance and invitation_pending(instance)),
            "counts": {
                "total": screens.screens_count(counts_levels),
                "view_only": view_only,
                "individual": individual,
            },
            "client_config": {
                "screens": screens.screens_payload(),
                "sections": [{"key": key, "name": name} for key, name in screens.SECTIONS],
                "groups": {
                    str(card["group"].pk): {
                        "name": card["group"].name,
                        "levels": card["levels"],
                        "scope": card["default_scope"],
                    }
                    for card in group_cards
                },
                "orgScope": SCOPE_ORG,
                "mode": "user",
            },
        }
        return render(self.request, self.template_name, context, status=status)

    def get(self, request, *args, **kwargs):
        instance = self.get_instance()
        groups = self.groups()
        form = UserEditorForm(instance=instance)
        return self.render(form, self.initial_selection(instance, groups), instance, groups)

    # -- gravação --------------------------------------------------------

    def post(self, request, *args, **kwargs):
        instance = self.get_instance()
        groups = self.groups()
        initial = self.initial_selection(instance, groups)
        selection = self.selection_from_post(instance, groups, initial)
        form = UserEditorForm(request.POST, instance=instance)
        form.is_valid()

        manage = self.can_manage_access() and not selection["complex"]
        if manage and instance is None and selection["group"] is None and not (
            self.can_set_superuser() and request.POST.get("is_superuser") == "on"
        ):
            form.add_error(None, "Escolha um grupo de acesso para a pessoa.")
        if instance is not None and instance.pk == request.user.pk and not form.cleaned_data.get("is_active", True):
            form.add_error("is_active", "Você não pode desativar o seu próprio acesso.")
        if form.errors:
            return self.render(form, selection, instance, groups, status=400)

        try:
            with transaction.atomic():
                user, created = self._save(form.cleaned_data, selection, instance, groups, manage)
        except (GroupError, CadastroError) as exc:
            form.add_error(None, str(exc))
            return self.render(form, selection, instance, groups, status=400)

        self._notify(form.cleaned_data, user, created)
        return redirect("user-list")

    def _save(self, data, selection, instance, groups, manage):
        request = self.request
        organization = self.organization
        mode = data["first_access"]
        created = instance is None

        if created:
            user = User(
                username=data["username"] or _unique_username(data["email"]),
                email=data["email"],
                first_name=data["first_name"],
                is_active=data["is_active"],
            )
            if mode == "password":
                user.set_password(data["password1"])
            else:
                user.set_unusable_password()
            user.save()
            AuditService.log(
                user=request.user,
                action=AuditLog.Action.USER_CREATED,
                target_user=user,
                reason=f"Usuário {user.username} cadastrado.",
            )
        else:
            user = instance
            changed = [
                label
                for label, before, after in (
                    ("nome", user.first_name, data["first_name"]),
                    ("e-mail", user.email, data["email"]),
                    ("usuário", user.username, data["username"] or user.username),
                    ("situação", user.is_active, data["is_active"]),
                )
                if before != after
            ]
            user.first_name = data["first_name"]
            user.email = data["email"]
            user.username = data["username"] or user.username
            user.is_active = data["is_active"]
            if mode == "password":
                user.set_password(data["password1"])
                AuditService.log(
                    user=request.user,
                    action=AuditLog.Action.PASSWORD_RESET,
                    target_user=user,
                    reason=f"Senha provisória de {user.username} definida.",
                )
            user.save()
            if changed:
                AuditService.log(
                    user=request.user,
                    action=AuditLog.Action.USER_UPDATED,
                    target_user=user,
                    reason=f"Dados alterados: {', '.join(changed)}.",
                )

        profile = user.profile
        profile.organization = organization
        profile.phone = data["phone"]
        if mode == "password":
            profile.must_change_password = True
        profile.main_sector_id = selection["main"]
        profile.save()

        self._sync_teams(user, selection)
        self._sync_superuser(user)

        if manage:
            group = next((g for g in groups if g.pk == selection["group"]), None)
            UserAccessService.apply(
                user, organization, group, selection["scope"], selection["levels"], request.user
            )
            self._guard_self_lockout(user)
        return user, created

    def _sync_teams(self, user, selection):
        sectors = list(Sector.objects.filter(pk__in=selection["teams"], organization=self.organization))
        managed = [s for s in sectors if selection["roles"].get(s.pk) == UserSector.Role.GESTOR]
        current = {
            m.sector_id: m.role for m in UserSector.objects.filter(user=user, removed_at__isnull=True)
        }
        wanted = {s.pk: selection["roles"].get(s.pk, UserSector.Role.MEMBRO) for s in sectors}
        if current != wanted:
            AccessService.sync_user_sectors(user, sectors, managed, self.request.user)

    def _sync_superuser(self, user):
        request = self.request
        if not self.can_set_superuser() or "is_superuser_field" not in request.POST:
            return
        wanted = request.POST.get("is_superuser") == "on"
        if wanted == user.is_superuser:
            return
        if not wanted:
            others = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=user.pk).exists()
            if not others:
                raise GroupError("Precisa existir pelo menos um super usuário ativo na plataforma.")
        user.is_superuser = wanted
        user.save(update_fields=["is_superuser"])
        AuditService.log(
            user=request.user,
            action=AuditLog.Action.SUPERUSER_CHANGED,
            target_user=user,
            old_value=str(not wanted),
            new_value=str(wanted),
            reason=f"Super usuário {'concedido a' if wanted else 'removido de'} {user.username}.",
        )

    def _guard_self_lockout(self, user):
        """Quem edita a si mesmo não pode sair da própria tela sem volta."""
        request = self.request
        if user.pk != request.user.pk or AuthorizationService.is_platform_admin(request.user):
            return
        for action in (catalog.USUARIO_EDITAR, catalog.SEGURANCA_GERIR_AUTORIZACOES):
            if not AuthorizationService.can(request.user, action):
                raise GroupError(
                    "Esta mudança tiraria o seu próprio acesso a Usuários ou a Grupos de acesso. "
                    "Peça a outra pessoa para alterar o seu grupo."
                )

    def _notify(self, data, user, created):
        request = self.request
        name = user.get_full_name() or user.get_username()
        mode = data["first_access"]
        if mode == "invite":
            try:
                send_invitation(request, user, request.user)
            except Exception:  # e-mail fora do ar não pode desfazer o cadastro
                messages.warning(
                    request,
                    f"{name} foi salvo, mas o e-mail do convite não pôde ser enviado. "
                    "Abra a pessoa e tente reenviar.",
                )
            else:
                AuditService.log(
                    user=request.user,
                    action=AuditLog.Action.USER_INVITED,
                    target_user=user,
                    reason=f"Convite enviado para {user.email}.",
                )
                messages.success(request, f"{name} salvo. Convite enviado para {user.email}.")
            return
        if mode == "password":
            messages.success(request, f"{name} salvo. A pessoa troca a senha provisória no primeiro acesso.")
            return
        messages.success(request, f"{name} salvo." if not created else f"{name} criado.")


# ---------------------------------------------------------------------------
# Grupos de acesso
# ---------------------------------------------------------------------------


class AccessGroupsMixin(OrganizationRequiredMixin, ActionRequiredMixin):
    """Ver os grupos exige `seguranca.gerir_perfis`; gravar exige também `seguranca.gerir_autorizacoes`."""

    required_action = catalog.SEGURANCA_GERIR_PERFIS

    def can_edit(self):
        return AuthorizationService.can(self.request.user, catalog.SEGURANCA_GERIR_AUTORIZACOES)


class AccessGroupsView(AccessGroupsMixin, TemplateView):
    template_name = "core/access_groups.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        groups = list(GroupService.groups(self.organization))
        selected_id = self.request.GET.get("grupo", "")
        selected = next((g for g in groups if str(g.pk) == selected_id), groups[0] if groups else None)

        keys = keys_by_profile([g.pk for g in groups])
        items = []
        for group in groups:
            levels = screens.levels_from_actions(keys[group.pk])
            items.append(
                {
                    "group": group,
                    "screens": screens.screens_count(levels),
                    "full": levels == screens.full_levels(),
                    "selected": selected is not None and group.pk == selected.pk,
                }
            )

        context.update(
            {
                "items": items,
                "group": selected,
                "can_edit": self.can_edit(),
                "read_only": not self.can_edit(),
                "can_manage_groups": AuthorizationService.can(self.request.user, catalog.SEGURANCA_GERIR_PERFIS),
                "tab": "editar",
                "total_screens": len(screens.SCREENS),
            }
        )
        if selected is not None:
            levels = screens.levels_from_actions(keys[selected.pk])
            extras, unmapped = advanced_summary(keys[selected.pk])
            context.update(
                {
                    "sections": screen_sections(levels),
                    "people": GroupService.user_count(selected),
                    "liberated": screens.screens_count(levels),
                    "extras": extras,
                    "unmapped": unmapped,
                    "client_config": {
                        "screens": screens.screens_payload(),
                        "sections": [{"key": key, "name": name} for key, name in screens.SECTIONS],
                        "levels": levels,
                        "mode": "group",
                    },
                }
            )
        context["copy_options"] = groups
        return context


class AccessGroupCreateView(AccessGroupsMixin, View):
    def post(self, request):
        if not self.can_edit():
            return self.handle_no_permission_message()
        copy_from = None
        raw = request.POST.get("copy_from", "")
        if raw.isdigit():
            copy_from = get_object_or_404(AccessProfile, pk=int(raw), organization=self.organization)
        try:
            group = GroupService.create(
                self.organization,
                request.POST.get("name", ""),
                request.POST.get("description", "").strip(),
                request.user,
                copy_from=copy_from,
            )
        except GroupError as exc:
            messages.error(request, str(exc))
            return redirect("access-groups")
        messages.success(request, f"Grupo “{group.name}” criado. Marque as telas e salve.")
        return redirect(f"{reverse('access-groups')}?grupo={group.pk}")

    def handle_no_permission_message(self):
        messages.error(self.request, "Você não tem permissão para criar grupos.")
        return redirect("access-groups")


class AccessGroupSaveView(AccessGroupsMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(AccessProfile, pk=pk, organization=self.organization)
        back = f"{reverse('access-groups')}?grupo={group.pk}"
        if not self.can_edit():
            messages.error(request, "Você não tem permissão para alterar grupos.")
            return redirect(back)

        try:
            name = request.POST.get("name", group.name)
            description = request.POST.get("description", group.description).strip()
            if (name.strip(), description) != (group.name, group.description):
                GroupService.rename(group, name, description, request.user)
            current = profile_levels(group)
            _, changed = GroupService.save_levels(group, levels_from_post(request.POST, current), request.user)
        except GroupError as exc:
            messages.error(request, str(exc))
            return redirect(back)

        people = GroupService.user_count(group)
        messages.success(
            request,
            f"Grupo “{group.name}” salvo. A mudança já vale para {people} pessoa{'s' if people != 1 else ''}.",
        )
        return redirect(back)


class AccessGroupInactivateView(AccessGroupsMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(AccessProfile, pk=pk, organization=self.organization, is_active=True)
        if not self.can_edit():
            messages.error(request, "Você não tem permissão para inativar grupos.")
            return redirect("access-groups")
        try:
            GroupService.inactivate(group, request.user)
        except GroupError as exc:
            messages.error(request, str(exc))
            return redirect(f"{reverse('access-groups')}?grupo={group.pk}")
        messages.success(request, f"Grupo “{group.name}” inativado.")
        return redirect("access-groups")


class AccessGroupsCompareView(AccessGroupsMixin, TemplateView):
    template_name = "core/access_groups_compare.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comparison = GroupService.comparison(self.organization)
        only_diff = self.request.GET.get("so_diferencas") == "1"
        sections = []
        for section in comparison["sections"]:
            rows = [row for row in section["rows"] if row["differs"] or not only_diff]
            if rows:
                sections.append({**section, "rows": rows})
        context.update(
            {
                "tab": "comparar",
                "groups": comparison["groups"],
                "sections": sections,
                "only_diff": only_diff,
                "labels": screens.LEVEL_LABELS,
            }
        )
        return context
