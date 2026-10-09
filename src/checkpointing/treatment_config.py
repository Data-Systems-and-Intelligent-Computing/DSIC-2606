def resolve_checkpoint_location(
    template,
    persistent_root,
    run_id,
    treatment,
    ephemeral_root=None,
):
    """Resolve an explicit per-run checkpoint path from the configured roots."""
    if not isinstance(template, str) or not template.strip():
        raise ValueError("checkpoint_location must be a non-empty template")
    if not run_id or not treatment:
        raise ValueError("run_id and treatment are required for checkpoint isolation")

    roots = {
        "persistent_root": persistent_root,
        "ephemeral_root": ephemeral_root,
    }

    for name, root in roots.items():
        placeholder = "{" + name + "}"
        if placeholder in template:
            if not root:
                raise ValueError(f"{name} is required by checkpoint_location")
            roots[name] = str(root).rstrip("/\\")

    try:
        return template.format(
            **roots,
            run_id=run_id,
            treatment=treatment,
        )
    except KeyError as exc:
        raise ValueError(f"unknown checkpoint template field: {exc.args[0]}") from exc