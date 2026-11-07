"""Opt-in portable attention experiment for pinned audio-driven Wan repos.

Uses query chunks and each sequence's real key length. This avoids requiring
FlashAttention2 on T4. It is a numerical fallback, NOT a quality/performance
claim. No upstream files are changed. Single-device only; distributed and
local-window attention are refused rather than approximated silently.
"""
from .registry import IntegrationError


def portable_attention(q, k, v, q_lens=None, k_lens=None, dropout_p=0.,
                       softmax_scale=None, q_scale=None, causal=False,
                       window_size=(-1, -1), deterministic=False,
                       dtype=None, version=None, chunk_size=256):
    import torch
    import torch.nn.functional as F
    if window_size != (-1, -1):
        raise IntegrationError('portable attention does not support local windows')
    if dropout_p:
        raise IntegrationError('portable inference attention requires dropout_p=0')
    if q.ndim != 4 or k.ndim != 4 or v.ndim != 4:
        raise IntegrationError('attention requires [batch, sequence, heads, dim]')
    if q.shape[0] != k.shape[0] or k.shape[:3] != v.shape[:3] or q.shape[2] != k.shape[2]:
        raise IntegrationError('attention batch/head/key/value dimensions mismatch')
    if not isinstance(chunk_size, int) or chunk_size < 1:
        raise IntegrationError('chunk_size must be a positive integer')
    batch, lq = q.shape[:2]
    lk = k.shape[1]
    q_lengths = [lq] * batch if q_lens is None else [int(n) for n in q_lens]
    k_lengths = [lk] * batch if k_lens is None else [int(n) for n in k_lens]
    if len(q_lengths) != batch or len(k_lengths) != batch:
        raise IntegrationError('one attention length per batch item is required')
    if any(not 0 < n <= lq for n in q_lengths) or any(not 0 < n <= lk for n in k_lengths):
        raise IntegrationError('attention lengths must be positive and within tensors')
    out = torch.zeros((batch,lq,q.shape[2],v.shape[-1]),device=q.device,dtype=q.dtype)
    for b in range(batch):
        kl = k_lengths[b]
        keys = k[b,:kl].transpose(0,1).unsqueeze(0)
        vals = v[b,:kl].transpose(0,1).unsqueeze(0)
        for start in range(0,q_lengths[b],chunk_size):
            end = min(start+chunk_size,q_lengths[b])
            queries=q[b,start:end].transpose(0,1).unsqueeze(0)
            if dtype is not None:
                queries, keys, vals = queries.to(dtype),keys.to(dtype),vals.to(dtype)
            if q_scale is not None:
                queries=queries*q_scale
            mask=None
            if causal:
                mask = (torch.arange(kl,device=q.device)[None,:] <=
                        torch.arange(start,end,device=q.device)[:,None])
            kwargs={} if softmax_scale is None else {'scale':softmax_scale}
            chunk=F.scaled_dot_product_attention(queries,keys,vals,
                     attn_mask=mask,dropout_p=0.,is_causal=False,**kwargs)
            out[b,start:end]=chunk.squeeze(0).transpose(0,1).to(out.dtype)
    return out


def install_portable_attention():
    """Patch imported aliases, not source files. Call after importing Wan.
    Explicit opt-in is required; CUDA distributed initialization is refused."""
    import sys
    import torch
    if torch.distributed.is_initialized() and torch.distributed.get_world_size() != 1:
        raise IntegrationError('portable attention is single-device only')
    import wan.modules.attention as module
    original=module.flash_attention
    replaced=[]
    for name,obj in list(sys.modules.items()):
        if name.startswith('wan.') and getattr(obj,'flash_attention',None) is original:
            setattr(obj,'flash_attention',portable_attention)
            replaced.append(name)
    if not replaced:
        raise IntegrationError('no Wan flash_attention aliases found')
    return replaced


def force_fp16_configs_for_t4():
    """Explicit experimental dtype override after Wan import; no source edit.
    T4 has no native bf16 support. This is not equivalent to validated output."""
    import torch
    from wan.configs import WAN_CONFIGS
    if not torch.cuda.is_available():
        raise IntegrationError('dtype override requires an actual CUDA host')
    if torch.cuda.get_device_capability()[0] != 7:
        raise IntegrationError('Turing-only override requested on a different GPU')
    updated=[]
    for key, cfg in WAN_CONFIGS.items():
        for name in ('param_dtype', 't5_dtype', 'clip_dtype'):
            if hasattr(cfg,name):
                setattr(cfg,name,torch.float16)
        updated.append(key)
    return updated
