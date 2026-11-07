import pytest
from forge.integrations.audio_context_adapter import normalize_singleton_text_context, install_context_adapter

class Tensor:
    dtype = 'float16'

def test_cpu_t5_context_then_cfg_wrapper_matches_model_contract():
    tensor = Tensor()
    cpu_t5_context = [tensor]
    arg_c = {'context': [cpu_t5_context]}
    fixed = normalize_singleton_text_context(arg_c['context'])
    assert fixed == [tensor]
    assert fixed[0].dtype == 'float16'
    assert arg_c['context'] == [[tensor]]

def test_normal_context_unchanged():
    normal = [Tensor()]
    assert normalize_singleton_text_context(normal) is normal

@pytest.mark.parametrize('bad', [[[]], [[Tensor(), Tensor()]], [[object()]], [[[Tensor()]]]])
def test_unexpected_nested_context_refused(bad):
    with pytest.raises(ValueError): normalize_singleton_text_context(bad)

def test_forward_adapter_maintains_other_inputs_and_is_idempotent():
    class Model:
        def forward(self, x, **kwargs): return x, kwargs
    model=Model(); install_context_adapter(model); first=model.forward
    install_context_adapter(model); assert model.forward is first
    tensor=Tensor(); x=object(); result, kwargs=model.forward(x, context=[[tensor]], t=123)
    assert result is x and kwargs['context']==[tensor] and kwargs['t']==123
