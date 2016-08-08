quark 1.0;

package gateway 1.0.0;

import mdk_discovery;

namespace gateway {

    class DiscoveryHandler {
        void connected() {}
        void active(Node node) {}
        void expire(Node node) {}
        void clear() {}
    }

    class GatewayDiscoveryClient extends Discovery {

        DiscoveryHandler handler;

        void _active(Node node)
    }
}