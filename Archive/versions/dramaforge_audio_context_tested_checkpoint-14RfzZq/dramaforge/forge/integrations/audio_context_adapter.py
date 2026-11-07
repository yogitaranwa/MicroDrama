"""Opt-in correction for the pinned audio pipelines' singleton CPU T5 nesting.

The encoder returns [tensor]. The CPU path preserves this list, then each
CFG call wraps it again. The model requires [tensor], never [[tensor]].
No upstream source or tensor values are changed.
"""
def normalize_singleton_text_context(context):
    if isinstance(context, list) and len(context) == 1 and isinstance(context[0], list):
        inner = context[0]
        if len(inner) != 1 or not hasattr(inner[0], 'dtype'):
            raise ValueError('only singleton tensor T5 context nesting is supported')
        return inner
    return context


def install_context_adapter(model):
    if getattr(model, '_forge_singleton_context_adapter', False):
        return
    original_forward = model.forward
    def forward(*args, **kwargs):
        if 'context' in kwargs:
            kwargs['context'] = normalize_singleton_text_context(kwargs['context'])
        return original_forward(*args, **kwargs)
    model.forward = forward
    model._forge_singleton_context_adapter = True
