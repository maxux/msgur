let hosturl = location.protocol + "//" + location.host + "/";

function create(message) {
    let key = uuid.v4();
    let cipher = CryptoJS.AES.encrypt(message, key);
    let encrypted = cipher.toString();

    return {key: key, encrypted: encrypted};
}

function decode(message, key) {
    let plain = CryptoJS.AES.decrypt(message, key);
    return plain.toString(CryptoJS.enc.Utf8);
}

function msgur(send) {
    let message = $("#message").val();
    let data = create(message);

    $("#summary").removeClass("d-none").show();

    if(send == true) {
        $("#creator").hide();
        $("#url-box").removeClass("d-none").show();
    }

    $("#key").html("Key: " + data.key);
    $("#encrypted").html("Encrypted: " + data.encrypted);

    let payload = {
        message: data.encrypted
    };

    if(send == true) {
        console.log(data);
        $.ajax("/create", {
            data: JSON.stringify(payload),
            contentType: 'application/json',
            type: 'POST',
            context: data,

        }).done(function(data) {
            let id = data.id;
            $("#url").val(hosturl + id + "#" + this.key);
        });
    }
}

function copyurl() {
    var input = document.body.appendChild(document.createElement("input"));
    input.value = $("#url").val();
    input.focus();
    input.select();

    document.execCommand('copy');
    input.parentNode.removeChild(input);

    $("#copy-btn").html("Copied !");
}

function fetch(context) {
    $("#mid").html("ID : " + context.id);
    $("#key").html("Key: " + context.key);

    $.ajax("/fetch/" + context.id, {
        context: context,
        statusCode: {
            404: function() {
                $("#error").removeClass("d-none").html("Message not found");
                $("#msgroot").hide();
            }
        },

    }).done(function(data) {
        let message = decode(data.message, this.key);
        $("#decrypt").html(message);
        $("#success").removeClass("d-none").html("Message retreived and destructed");
    });

}

function loader() {
    let context = {
        id: $(location).attr('pathname').substr(1),
        key: $(location).attr('hash').substr(1),
    };

    if(context.id == '' || context.key == '') {
        $("#message").focus();
        return;
    }

    fetch(context);
}

$(document).ready(loader);
