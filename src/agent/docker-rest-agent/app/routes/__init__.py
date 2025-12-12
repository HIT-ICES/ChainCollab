from . import network, nodes, ca, eth, ports, ipfs


def register_routes(app):
    app.register_blueprint(network.bp, url_prefix="/api/v1")
    app.register_blueprint(nodes.bp, url_prefix="/api/v1")
    app.register_blueprint(ca.bp, url_prefix="/api/v1")
    app.register_blueprint(eth.bp, url_prefix="/api/v1")
    app.register_blueprint(ports.bp, url_prefix="/api/v1")
    app.register_blueprint(ipfs.bp, url_prefix="/api/v1")
