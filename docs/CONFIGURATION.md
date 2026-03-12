# Configuration

Primary runtime configuration is stored in `src/config.yaml`.

## Core Keys

- `MODE`: `database` or `server`
- `HOST_IP`, `HOST_PORT`
- `SECRET_KEY`
- `SQLALCHEMY_DATABASE_URI`
- `PKI_CERT_PATH`, `PKI_CERT`, `PKI_KEY`

## WireGuard Defaults

- `BASE_IP`, `BASE_NETMASK`
- `BASE_PORT`
- `BASE_DNS`
- `PEER_ACTIVITY_TIMEOUT`

## Security Notes

- Replace default `SECRET_KEY` before production.
- Use least-privilege user for the Flask process.
- Restrict UI network access with firewall/reverse-proxy ACLs.
- Avoid storing privileged credentials in plain text where possible.
