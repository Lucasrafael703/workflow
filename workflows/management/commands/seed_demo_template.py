from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from workflows.models import Priority, ProcessTemplate, ProcessTemplateStep

User = get_user_model()

# Etapas do processo comercial de orçamento/proposta (seção 32 da especificação).
# Isto é dado de configuração inicial, não lógica de código: o usuário autorizado
# pode alterar/reordenar/inserir/remover etapas depois, via Admin ou pela tela de
# edição de workflow, sem tocar neste comando.
STEPS = [
    ("Entrada da oportunidade", "COMERCIAL", 1, Priority.NORMAL),
    ("Aguardando documentos", "COMERCIAL", 3, Priority.NORMAL),
    ("Análise inicial", "COMERCIAL", 2, Priority.NORMAL),
    ("Levantamento de quantidades de materiais", "ENGENHARIA", 5, Priority.NORMAL),
    ("Cotação de materiais", "SUPRIMENTOS", 5, Priority.NORMAL),
    ("Levantamento de mão de obra direta", "ENGENHARIA", 3, Priority.NORMAL),
    ("Levantamento de custos indiretos", "FINANCEIRO", 3, Priority.NORMAL),
    ("Montagem da planilha orçamentária", "ENGENHARIA", 4, Priority.ALTA),
    ("Montagem da proposta técnica e comercial", "COMERCIAL", 3, Priority.ALTA),
    ("Revisão interna", "COMERCIAL", 2, Priority.ALTA),
    ("Envio da proposta por e-mail", "COMERCIAL", 1, Priority.NORMAL),
    ("Follow-up", "COMERCIAL", 5, Priority.NORMAL),
    ("Negociação", "COMERCIAL", 7, Priority.NORMAL),
    ("Fechamento ou perda", "COMERCIAL", 3, Priority.NORMAL),
    ("Elaboração do contrato", "FINANCEIRO", 5, Priority.NORMAL),
    ("Kick-off", "PLANEJAMENTO", 2, Priority.NORMAL),
]


class Command(BaseCommand):
    help = "Cria o template de demonstração 'Orçamento Comercial - Engenharia Civil' com as etapas da especificação."

    def handle(self, *args, **options):
        creator = User.objects.filter(is_superuser=True).order_by("id").first()
        if not creator:
            self.stderr.write(self.style.ERROR("Crie um superusuário antes de rodar este comando."))
            return

        template, created = ProcessTemplate.objects.get_or_create(
            name="Orçamento Comercial - Engenharia Civil",
            defaults={"description": "Processo comercial de orçamento/proposta.", "created_by": creator},
        )
        if not created:
            self.stdout.write("Template já existia, atualizando etapas...")
            template.steps.all().delete()

        for order, (name, group_name, deadline_days, priority) in enumerate(STEPS, start=1):
            group, _ = Group.objects.get_or_create(name=group_name)
            ProcessTemplateStep.objects.create(
                template=template,
                order=order,
                name=name,
                responsible_group=group,
                default_deadline_days=deadline_days,
                default_priority=priority,
            )

        self.stdout.write(self.style.SUCCESS(f"Template '{template.name}' criado/atualizado com {len(STEPS)} etapas."))
