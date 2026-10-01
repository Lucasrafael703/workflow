"""O que a LPS entende de uma solicitação recebida.

`suggest()` é a única porta de entrada: hoje usa regras locais (nomes cadastrados,
domínio do e-mail, datas em português); trocar por outro leitor, como uma IA, é
reescrever esta função sem tocar no resto. O resultado é sempre só um ponto de
partida — quem faz a triagem confere, e cada acerto traz o motivo ("reasons").
"""

from collections import Counter
from dataclasses import dataclass, field

from django.utils import timezone

from core.models import Client, Sector, Site

from . import textparse

# Quanto cada acerto soma à confiança (o máximo possível é 100).
POINTS_TITLE_FROM_SUBJECT = 15
POINTS_TITLE_FROM_LINE = 5
POINTS_CLIENT = 35
POINTS_SITE = 15
POINTS_SECTOR_FROM_SUBJECT = 10
POINTS_SECTOR_FROM_HISTORY = 5
POINTS_DEADLINE = 25

# Quantas atividades recentes do cliente entram no histórico de setor, e quantas
# vezes o setor precisa aparecer para virar sugestão.
HISTORY_ACTIVITIES = 10
HISTORY_MIN_REPEATS = 2
MIN_NAME_LENGTH = 3


@dataclass
class Suggestion:
    title: str = ""
    client: Client = None
    site: Site = None
    sector: Sector = None
    deadline: object = None  # datetime com fuso
    confidence: int = 0
    reasons: list = field(default_factory=list)


def _matching_names(records, haystack):
    """Registros cujo nome aparece no texto, sem os que são parte do nome de outro.

    Se "Convivy" e "Convivy Engenharia" aparecem, só a segunda vale: o nome mais
    longo é o que a pessoa de fato citou.
    """
    found = []
    for record in records:
        normalized = textparse.normalize(record.name)
        if len(normalized) >= MIN_NAME_LENGTH and textparse.contains_phrase(haystack, normalized):
            found.append((record, normalized))
    return [
        record
        for record, normalized in found
        if not any(normalized != other and normalized in other for _, other in found)
    ]


def _pick_client(organization, haystack, sender_email, reasons):
    clients = list(Client.objects.filter(organization=organization, is_active=True))

    by_name = _matching_names(clients, haystack)
    domain = textparse.email_domain(sender_email)
    by_domain = []
    if domain and not textparse.is_free_domain(domain):
        by_domain = [
            client
            for client in clients
            if textparse.same_domain(domain, textparse.email_domain(client.email))
        ]

    if len(by_name) == 1:
        reasons.append(f"Cliente: \"{by_name[0].name}\" aparece no texto")
        return by_name[0]
    if len(by_name) > 1:
        # O domínio do remetente pode desempatar entre os nomes citados.
        tie_break = [client for client in by_name if client in by_domain]
        if len(tie_break) == 1:
            reasons.append(f"Cliente: \"{tie_break[0].name}\" aparece no texto e é o domínio do remetente")
            return tie_break[0]
        reasons.append("Cliente não identificado: mais de um cliente citado")
        return None
    if len(by_domain) == 1:
        reasons.append(f"Cliente: o e-mail do remetente é do domínio de \"{by_domain[0].name}\"")
        return by_domain[0]
    if len(by_domain) > 1:
        reasons.append("Cliente não identificado: o domínio do remetente serve a mais de um cliente")
    return None


def _pick_site(organization, client, haystack, reasons):
    sites = Site.objects.filter(organization=organization, is_active=True).select_related("client")
    if client is not None:
        # Obra de outro cliente não serve; obra sem cliente serve para qualquer um.
        sites = [site for site in sites if site.client_id in (None, client.pk)]
    else:
        sites = list(sites)

    found = _matching_names(sites, haystack)
    if len(found) == 1:
        reasons.append(f"Obra: \"{found[0].name}\" aparece no texto")
        return found[0]
    if len(found) > 1:
        reasons.append("Obra não identificada: mais de uma obra citada")
    return None


def _pick_sector(organization, client, subject_normalized, reasons):
    """Setor citado no assunto; senão o que mais atendeu esse cliente."""
    sectors = list(Sector.objects.filter(organization=organization, is_active=True))
    in_subject = _matching_names(sectors, subject_normalized)
    if len(in_subject) == 1:
        reasons.append(f"Setor: \"{in_subject[0].name}\" aparece no assunto")
        return in_subject[0], POINTS_SECTOR_FROM_SUBJECT

    if client is not None:
        from activities.models import Activity

        recent = (
            Activity.objects.filter(organization=organization, client=client, sector__isnull=False)
            .order_by("-created_at")
            .values_list("sector_id", flat=True)[:HISTORY_ACTIVITIES]
        )
        ranking = Counter(recent).most_common(2)
        if ranking and ranking[0][1] >= HISTORY_MIN_REPEATS and (len(ranking) == 1 or ranking[0][1] > ranking[1][1]):
            sector = next((item for item in sectors if item.pk == ranking[0][0]), None)
            if sector is not None:
                reasons.append(
                    f"Setor: as últimas atividades de \"{client.name}\" foram para \"{sector.name}\""
                )
                return sector, POINTS_SECTOR_FROM_HISTORY
    return None, 0


def suggest(organization, *, subject="", raw_content="", sender_name="", sender_email="", received_at=None):
    """Lê a solicitação e devolve o que conseguiu entender (nunca levanta por texto estranho)."""
    received_at = received_at or timezone.now()
    reasons = []
    score = 0

    cleaned_subject = textparse.clean_subject(subject)
    subject_normalized = textparse.normalize(cleaned_subject)
    haystack = f"{subject_normalized}\n{textparse.normalize(raw_content)}"

    if cleaned_subject:
        title, score = cleaned_subject, score + POINTS_TITLE_FROM_SUBJECT
        reasons.append("Título: tirado do assunto")
    else:
        title = textparse.first_useful_line(raw_content)
        if title:
            score += POINTS_TITLE_FROM_LINE
            reasons.append("Título: tirado da primeira linha do texto")

    client = _pick_client(organization, haystack, sender_email, reasons)
    site = _pick_site(organization, client, haystack, reasons)
    if client is None and site is not None and site.client is not None and site.client.is_active:
        # A obra só pertence a um cliente: citar a obra já diz quem pediu.
        client = site.client
        reasons.append(f"Cliente: a obra \"{site.name}\" pertence a \"{client.name}\"")
    if client is not None:
        score += POINTS_CLIENT
    if site is not None:
        score += POINTS_SITE

    sector, sector_points = _pick_sector(organization, client, subject_normalized, reasons)
    score += sector_points

    deadline = textparse.parse_deadline(cleaned_subject, received_at, require_cue=False) or textparse.parse_deadline(
        raw_content, received_at
    )
    if deadline is not None:
        score += POINTS_DEADLINE
        reasons.append(deadline.reason)

    return Suggestion(
        title=title,
        client=client,
        site=site,
        sector=sector,
        deadline=deadline.value if deadline else None,
        confidence=min(100, score),
        reasons=reasons,
    )
