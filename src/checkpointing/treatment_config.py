def resolve_checkpoint_location(template, persistent_root, run_id, treatment):
    """Resolve the checkpoint target; None means checkpointing is disabled."""
    if template is None:
        return None
    if not isinstance(template, str) or not template.strip():
        raise ValueError("checkpoint_location must be null or a non-empty template")
    if not persistent_root:
        raise ValueError("B1 requires a selected persistent checkpoint root")
    if not run_id or not treatment:
        raise ValueError("run_id and treatment are required for checkpoint isolation")

    root = str(persistent_root).rstrip("/\\")
    return template.format(
        persistent_root=root,
        run_id=run_id,
        treatment=treatment,
    )