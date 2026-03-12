from gui.models import Network


class NetworkRepository:
    @staticmethod
    def get(network_id: int) -> Network | None:
        return Network.query.get(network_id)

    @staticmethod
    def all() -> list[Network]:
        return Network.query.all()
