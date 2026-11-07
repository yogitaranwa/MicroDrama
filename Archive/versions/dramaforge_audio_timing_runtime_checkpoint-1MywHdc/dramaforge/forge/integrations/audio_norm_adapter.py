"""Opt-in fp16 audio projection LayerNorm input alignment for T4 validation.

Quantized proj3 can emit fp32 while CPU-offload wrappers compute LayerNorm
with fp16 weights. Align only that norm's input, not weights or model values.
"""
def install_audio_norm_adapter(model):
    norm = model.audio_proj.norm
    if getattr(norm, '_forge_audio_norm_dtype_adapter', False):
        return
    import torch
    target_dtype = getattr(norm, 'computation_dtype', None)
    if target_dtype is None:
        target_dtype = next(norm.parameters()).dtype
    if target_dtype not in (torch.float16, torch.float32, torch.bfloat16):
        raise ValueError('unsupported audio norm computation dtype')
    def align_input(module, args):
        if not args or not isinstance(args[0], torch.Tensor):
            raise ValueError('tensor audio norm input required')
        return (args[0].to(dtype=target_dtype),) + args[1:]
    norm.register_forward_pre_hook(align_input)
    norm._forge_audio_norm_dtype_adapter = True
