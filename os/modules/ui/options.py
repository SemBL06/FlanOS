import modules.ui_core as ui_core


def show(ctx, items=None, field=None, selected=0, marker="*"):
    return ui_core.options(
        ctx,
        items=items,
        field=field,
        selected=selected,
        marker=marker,
        handle_input=False
    )


def move(ctx, direction=None):
    return ui_core.options_move(ctx, direction)


def current(ctx):
    return ui_core.options_current(ctx)


def index(ctx):
    return ui_core.options_index(ctx)


def interact(ctx, items=None, field=None, selected=None, marker=None, run=False):
    result = ui_core.options(
        ctx,
        items=items,
        field=field,
        selected=selected if selected is not None else 0,
        marker=marker or "*",
        handle_input=True
    )

    if run and ui_core.last_action(ctx) == "select" and isinstance(result, dict) and result.get("type") == "script":
        system_module = ctx.executor.modules.get("system", {})
        runner = system_module.get("run")
        if callable(runner):
            runner(ctx, result)

    return result


def get_module():
    return {
        "show": show,
        "move": move,
        "current": current,
        "index": index,
        "interact": interact
    }
