
function randomString(length) {
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < length; i++)
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}

$(document).foundation();
$(document).ready(function () {
    let clientId = 'clientId-' + randomString(10);
    fetch(`${websocket_origin}/oauth/user`)
    .then(resp => resp.json())
    .then(data => {
        console.log('User info', data);
        user_id = data['_id']
        session_id = data['session_id']
        password = data['client_token']
        $('#urlInput').val(websocket_server);
        $('#portInput').val(websocket_port);
        $('#userInput').val(session_id);
        $('#pwInput').val(password);
        $('#subscribeTopic').val(`${user_id}/notify`);
        $('#publishTopic').val(`${user_id}/notify`);
        $('#lwTopicInput').val(`${user_id}/last-will`);
        $('#sslInput').prop('checked', websocket_ssl);
        $('#clientIdInput').val(clientId);
        $('#LWMInput').val(`${clientId} is gone with the wind!!`);
        $('#colorChooser').minicolors();
        $("#addSubButton").fancybox({
            'afterShow': function () {
                var rndColor = websocketclient.getRandomColor();
                $("#colorChooser").minicolors('value', rndColor);
            }
        });

        websocketclient.render.toggle('publish');
        websocketclient.render.toggle('messages');
        websocketclient.render.toggle('sub');

    })
});