import re
import hashlib
import secrets
from datetime import datetime
from urllib.parse import quote


RX_TOKEN = re.compile(r"^[a-zA-Z0-9_\-]{64}$")
SZ_TOKEN_BYTES = 48


def gen_token():
    return secrets.token_urlsafe(SZ_TOKEN_BYTES)


def hash_n_length(content, block_size=256 * 1024):
    length = 0
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: content.read(block_size), b''):
        sha256.update(chunk)
        length += len(chunk)

    content.seek(0)
    return sha256.hexdigest(), length


def presigned_url(self, handle, expire_in_days=7, response_headers=None):
    handle = coerce_handle(handle)
    quoted_name = quote(handle.name)
    headers = {
        'response-content-disposition': 'inline;filename={}'.format(quoted_name),
        'response-content-type': handle.content_type
    }

    if isinstance(response_headers, dict):
        headers.update(response_headers)

    if expire_in_days > 1:
        exp_dt = timedelta(days=expire_in_days)
        utc_now = datetime.utcnow()
        cdn_exp = handle.cdn_exp.replace(tzinfo=None) if getattr(
            handle, 'cdn_url', False) else None
        if (getattr(handle, 'cdn_url', False)
                and cdn_exp > (utc_now + timedelta(days=1))):
            return handle.cdn_url

        cdn_exp = utc_now + exp_dt
        cdn_url = self._client.presigned_get_object(
            handle.bucket or self.s3_get_bucket,
            handle.filehash,
            expires=exp_dt,
            response_headers=headers
        )

        return cdn_url, cdn_exp
