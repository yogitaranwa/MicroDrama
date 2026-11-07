"""Small GPU numerical test only, no models or downloads.
Run with dramaforge on PYTHONPATH after model_setup_preflight."""
import json,time
import torch
from forge.integrations.t4_attention import portable_attention
assert torch.cuda.is_available()
torch.manual_seed(42)
q,k,v=[torch.randn(1,n,8,64,device='cuda',dtype=torch.float16) for n in (257,389,389)]
t0=time.time()
a=portable_attention(q,k,v,q_lens=[257],k_lens=[331],dtype=torch.float16,chunk_size=64)
b=torch.nn.functional.scaled_dot_product_attention(
    q.transpose(1,2),k[:,:331].transpose(1,2),v[:,:331].transpose(1,2)).transpose(1,2)
torch.testing.assert_close(a,b,rtol=0.02,atol=0.002)
print(json.dumps({'cuda':torch.cuda.get_device_name(0),'max_abs_difference':(a-b).abs().max().item(),
                  'seconds':time.time()-t0,'status':'numerical_test_only_not_inference'}))

# Real Wan RoPE uses float32 queries/keys with half-precision values.
qm,km=q.float(),k.float()
am=portable_attention(qm,km,v,k_lens=[331],chunk_size=64)
torch.testing.assert_close(am,b.float(),rtol=0.02,atol=0.002)
assert torch.isfinite(am).all()
print(json.dumps({'status':'mixed_rotary_dtype_numerical_test_only',
    'max_abs_difference':(am-b.float()).abs().max().item()}))
