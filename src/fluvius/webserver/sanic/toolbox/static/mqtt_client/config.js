websocket_origin = window.location.origin;
websocket_server = document.domain;
websocket_protocol = window.location.protocol;
websocket_ssl = (websocket_protocol == 'https:');
websocket_port = window.location.port || (websocket_ssl ? 443 : 9001);
