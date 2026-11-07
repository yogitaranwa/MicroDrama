from types import SimpleNamespace
import torch
from forge.integrations.audio_norm_adapter import install_audio_norm_adapter

def test_real_half_layernorm_accepts_float_projection_after_adapter():
    norm=torch.nn.LayerNorm(4).half()
    model=SimpleNamespace(audio_proj=SimpleNamespace(norm=norm))
    x=torch.tensor([[.1,.2,.3,.4]],dtype=torch.float32)
    expected=norm(x.half())
    install_audio_norm_adapter(model)
    actual=norm(x)
    assert actual.dtype==torch.float16
    assert torch.allclose(actual,expected)
    assert norm.weight.dtype==torch.float16

def test_offload_wrapper_computation_dtype_and_idempotence():
    class Wrapper(torch.nn.Module):
        computation_dtype=torch.float16
        def __init__(self):super().__init__();self.module=torch.nn.LayerNorm(4).float()
        def forward(self,x):return torch.nn.functional.layer_norm(x,(4,),self.module.weight.half(),self.module.bias.half())
    norm=Wrapper();model=SimpleNamespace(audio_proj=SimpleNamespace(norm=norm))
    install_audio_norm_adapter(model);install_audio_norm_adapter(model)
    assert len(norm._forward_pre_hooks)==1
    assert norm(torch.randn(2,4)).dtype==torch.float16
    assert norm.module.weight.dtype==torch.float32
