"""Auxiliares para montar processos nos testes.

Cria o molde direto pelo ORM (sem passar por `ProcessService`), para que os
testes de aplicação/execução não dependam das permissões de edição de
processo — o que está sob teste ali é o que acontece *depois* de publicado.
"""

from django.utils import timezone

from .models import Process, ProcessCriterion, ProcessInput, ProcessStep, ProcessVersion


def build_process(
    organization,
    company,
    created_by,
    name="Orçamento",
    steps=(),
    inputs=(),
    criteria=(),
    output_description="Proposta comercial pronta para envio",
    evidence_type=ProcessVersion.EvidenceType.CONFIRMACAO,
    publish=True,
    number=1,
    process=None,
    is_active=True,
):
    """Cria (ou estende) um processo e devolve a `ProcessVersion`.

    `steps`: dicts com `name`, `sector` e, opcionalmente, `depends_on_previous`
    (padrão `True`) e `default_responsavel`.
    `inputs`: dicts com `name` e, opcionalmente, `type` (`TEXTO`), `required`
    (`True`), `source` e `help_text`.
    `criteria`: dicts com `name` e, opcionalmente, `required` (`True`).
    """
    if process is None:
        process = Process.objects.create(
            organization=organization, company=company, name=name, created_by=created_by, is_active=is_active
        )
    version = ProcessVersion.objects.create(
        process=process,
        number=number,
        created_by=created_by,
        output_description=output_description,
        output_evidence_type=evidence_type,
    )
    for order, spec in enumerate(steps, start=1):
        ProcessStep.objects.create(
            version=version,
            sector=spec["sector"],
            name=spec["name"],
            order=order,
            depends_on_previous=spec.get("depends_on_previous", True),
            default_responsavel=spec.get("default_responsavel"),
        )
    for order, spec in enumerate(inputs, start=1):
        ProcessInput.objects.create(
            version=version,
            name=spec["name"],
            input_type=spec.get("type", ProcessInput.InputType.TEXTO),
            is_required=spec.get("required", True),
            source=spec.get("source", ""),
            help_text=spec.get("help_text", ""),
            order=order,
        )
    for order, spec in enumerate(criteria, start=1):
        ProcessCriterion.objects.create(
            version=version, name=spec["name"], is_required=spec.get("required", True), order=order
        )
    if publish:
        publish_version(version, created_by)
    return version


def publish_version(version, user):
    """Publica a versão como `ProcessService.publish` faz: a anterior vira substituída."""
    version.process.versions.filter(status=ProcessVersion.Status.PUBLICADO).exclude(pk=version.pk).update(
        status=ProcessVersion.Status.SUBSTITUIDO
    )
    version.status = ProcessVersion.Status.PUBLICADO
    version.published_by = user
    version.published_at = timezone.now()
    version.save(update_fields=["status", "published_by", "published_at"])
    return version
