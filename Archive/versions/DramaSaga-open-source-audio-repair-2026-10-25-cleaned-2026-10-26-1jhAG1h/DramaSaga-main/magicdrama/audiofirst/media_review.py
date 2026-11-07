"""Hash-bound review declarations. Evidence of a statement, not independent proof."""
import datetime as dt
from .core import digest

CHECKS=('action','identity','wardrobe','camera','eyelines','props','speech_ownership','expression','lip_sync')


def require_media_review(asset, input_sha256):
    receipt=asset.get('review',{})
    if receipt.get('asset_sha256')!=digest(asset['path']) or receipt.get('input_sha256')!=input_sha256:
        raise ValueError('Review is stale for rendered bytes or shot inputs')
    if not isinstance(receipt.get('reviewer'),str) or not receipt['reviewer'].strip():
        raise ValueError('Named media reviewer required')
    try:
        stamp=dt.datetime.fromisoformat(receipt.get('reviewed_at','').replace('Z','+00:00'))
        if stamp.tzinfo is None or stamp>dt.datetime.now(dt.timezone.utc):raise ValueError
    except (ValueError,TypeError,AttributeError) as error:
        raise ValueError('Valid timezone-aware nonfuture media review timestamp required') from error
    if any(receipt.get('checks',{}).get(k) is not True for k in CHECKS):
        raise ValueError('Action/continuity/camera/speech review incomplete; unknown is not pass')
    return receipt
