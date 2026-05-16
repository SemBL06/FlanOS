import modules.ui_core as ui_core


def show(ctx, value=None, title=None):
    return ui_core.description(
        ctx,
        value=value,
        title=title,
        handle_input=False
    )


def get_module():
    return {
        "show": show
    }
