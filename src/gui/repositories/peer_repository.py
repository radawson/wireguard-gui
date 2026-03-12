from gui.models import Peer


class PeerRepository:
    @staticmethod
    def get(peer_id: int) -> Peer | None:
        return Peer.query.get(peer_id)

    @staticmethod
    def all() -> list[Peer]:
        return Peer.query.all()

    @staticmethod
    def by_network(network_id: int) -> list[Peer]:
        return Peer.query.filter_by(network_id=network_id).all()
