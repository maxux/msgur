"use strict";

//
// Msgur is fully implemented client side. All cryptographic operations
// are done in the browser and keys are never exchanged implicitly.
//

class KeysManager {
    constructor() {
        this.utf8_decoder = new TextDecoder();
        this.utf8_encoder = new TextEncoder();
    }

    //
    // Keys Generator
    //
    async generate_onetime_key() {
        const params = {
            name: "AES-GCM",
            length: 128
        };

        // Generate a new random Symetric Key
        const key = await window.crypto.subtle.generateKey(params, true, ["encrypt"]);
        const iv = window.crypto.getRandomValues(new Uint8Array(12));

        return {key: key, iv: iv};
    }

    async export_onetime_key(key, iv) {
        const keyout = await window.crypto.subtle.exportKey("raw", key);
        const hexkey = new Uint8Array(keyout).toHex();
        const hexiv = iv.toHex();

        return {key: hexkey, iv: hexiv};
    }

    async load_onetime_key(hexkey) {
        const params = "AES-GCM";

        const raw = await Uint8Array.fromHex(hexkey);
        const key = await window.crypto.subtle.importKey("raw", raw, params, true, ["decrypt"]);

        return {key: key};
    }

    //
    // Cipher Processing
    //
    async encrypt_plaintext(key, iv, plaintext) {
        // Encode input text in utf-8
        const encoded = this.utf8_encoder.encode(plaintext);

        // Setup encryption kntxt
        const params = {
            name: "AES-GCM",
            iv
        };

        // Encrypt the encoded message with configured AES-GCM key
        const ciphertext = await window.crypto.subtle.encrypt(params, key, encoded);
        const dataview = new Uint8Array(ciphertext);

        return {ciphertext: dataview};
    }

    async decrypt_ciphertext(key, hexcipher, hexiv) {
        const data = await Uint8Array.fromBase64(hexcipher);
        const iv = await Uint8Array.fromHex(hexiv);

        // Setup encryption kntxt
        const params = {
            name: "AES-GCM",
            iv
        };

        // Decrypt the ciphertext with the key and the provided iv
        const encoded = await window.crypto.subtle.decrypt(params, key, data);

        // Encode input text in utf-8
        const plaintext = await this.utf8_decoder.decode(encoded);

        return {plaintext: plaintext};
    }
}

class SecureMessenger {
    constructor() {
        // Single time computed baseurl
        this.baseurl = `${location.protocol}//${location.host}`;

        // Internal Keys Manager
        this.keys = new KeysManager();
    }

    //
    // Helpers
    //
    copy_to_clipboard(data, source) {
        const link = data.dataset.link;

        navigator.clipboard.writeText(link).then(() => {
            source.innerText = "Clipboard updated";
            source.classList.remove("btn-outline-teal");
            source.classList.add("btn-success");

        },() => {
            source.innerText = "Clipboard operation failed";
            source.disabled = true;
            source.classList.remove("btn-outline-teal");
            source.classList.add("btn-danger");
        });
    }

    show_success_message(message) {
        document.getElementById("success").classList.remove("d-none");
        document.getElementById("success").innerText = message;
        document.getElementById("fetch-ready").classList.remove("d-none");
    }

    show_error_message(message) {
        document.getElementById("error").classList.remove("d-none");
        document.getElementById("error").innerText = message;
    }

    reset_error_success_message() {
        document.getElementById("error").classList.add("d-none");
        document.getElementById("error").innerText = "";
        // document.getElementById("success").classList.add("d-none");
        // document.getElementById("success").innerText = "";

    }

    //
    // Save encrypted message on the server
    //
    async remote_push_ciphertext(message, iv) {
        const payload = {
            message: message,
            iv: iv,
        };

        const req = new Request("/api/create", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });

        const response = await fetch(req);
        if(!response.ok) {
            throw new Error(`Unhandled status: ${response.status}`);
        }

        const saved = await response.json();

        return {fetch: `${this.baseurl}/${saved.id}`, id: saved.id};
    }

    //
    // Encrypt ciphertext
    //
    async encrypt_plaintext_data(plaintext) {
        const keygen = await this.keys.generate_onetime_key();

        // Encrypt data with plain low level objects
        const key = keygen.key;
        const iv = keygen.iv;
        const data = await this.keys.encrypt_plaintext(key, iv, plaintext);

        // Nicely serialize evetything
        const packed = await this.keys.export_onetime_key(key, iv);
        const encoded = data.ciphertext.toBase64();

        return {key: packed.key, iv: packed.iv, data: encoded};
    }

    async event_request_encrypt(event) {
        // Pending ID waiting for server response
        document.getElementById("create-id").innerText = "...";

        try {
            const plaintext = document.getElementById("message").value;
            if(plaintext.length == 0) {
                throw new Error("Your message should not be empty.");
            }

            const cipher = await this.encrypt_plaintext_data(plaintext);

            document.getElementById("create-key").innerText = cipher.key;
            document.getElementById("create-iv").innerText = cipher.iv;
            // document.getElementById("encrypted").innerText = cipher.data;

            if(event.target.id != "encrypt-and-send") {
                // No send, only encrypt requested
                document.getElementById("create-info").classList.remove("d-none");
                document.getElementById("creator").classList.add("d-none");
                return false;
            }

            const srv = await this.remote_push_ciphertext(cipher.data, cipher.iv);
            const url = `${srv.fetch}#${cipher.key}`;

            document.getElementById("create-id").innerText = srv.id;
            document.getElementById("public-url").innerText = url;
            document.getElementById("public-url").dataset.link = url;

            return url;

        } catch(error) {
            throw error;
        }
    }

    //
    // Decrypt ciphertext
    //
    request_presents_data(iv, plaintext) {
        document.getElementById("fetch-iv").innerText = iv;
        document.getElementById("plaintext-area").innerText = plaintext;

        // let msg = "This message is now removed from the server.";
        // this.notification_trigger(msg, 8000);

        this.show_success_message("This message is now removed from the server.");
    }

    async request_decode_data(key, info) {
        const text = await this.keys.decrypt_ciphertext(key.key, info.ciphertext, info.iv);
        return text.plaintext
    }

    async request_processor(kntxt, msginfo) {
        const key = await this.keys.load_onetime_key(kntxt.key);
        const plaintext = await this.request_decode_data(key, msginfo);

        return this.request_presents_data(msginfo.iv, plaintext);
    }

    async request_message(kntxt) {
        // Presents settings we already found
        document.getElementById("fetch-id").innerText = kntxt.id;
        document.getElementById("fetch-key").innerText = kntxt.key;

        // Prepare the remote HTTP request
        const req = new Request(`/api/fetch/${kntxt.id}`);

        // Request message data from the server
        const response = await window.fetch(req);
        if(!response.ok) {
            // Explicit missing message
            if(response.status == 404) {
                throw new Error("Message not found on the server");
            }

            // Something unexpected happened
            throw new Error(`Unhandled status: ${response.status}`);
        }

        // Process Message Info
        const msginfo = await response.json();
        const data = await this.request_processor(kntxt, msginfo);

        this.reset_error_success_message();
    }

    //
    //
    //
    initialize_editor() {
        const sendbtn = document.getElementById("encrypt-and-send");
        if(!sendbtn) {
            // No message form available
            return;
        }

        function send_reset() {
            sendbtn.disabled = false;
            sendbtn.innerText = "Encrypt and Send";
        }

        sendbtn.addEventListener("click", (event) => {
            this.reset_error_success_message();

            sendbtn.disabled = true;
            sendbtn.innerText = "Saving, please wait";

            this.event_request_encrypt(event).then(
                (x) => {
                    document.getElementById("create-info").classList.remove("d-none");
                    document.getElementById("creator").classList.add("d-none");
                    if(x) {
                        document.getElementById("upload-ok").classList.remove("d-none");
                    }
                },
                (a) => {
                    send_reset();
                    this.show_error_message(a);
                }
            );
        });

        document.getElementById("message").focus();

        document.getElementById("new-message").addEventListener("click", (event) => {
            event.stopPropagation();
            event.preventDefault();

            this.reset_error_success_message();
            send_reset();
            document.getElementById("create-info").classList.add("d-none");
            document.getElementById("creator").classList.remove("d-none");
            document.getElementById("upload-ok").classList.add("d-none");
            document.getElementById("message").value = "";
            document.getElementById("message").focus();
        });

        document.getElementById("copy-btn").addEventListener("click", (event) => {
            event.stopPropagation();
            event.preventDefault();

            const source = document.getElementById("public-url");
            this.copy_to_clipboard(source, event.target);
        });
    }

    // Show a modal with description of the problem with Crypto
    modal_crypto_failed() {
        const oops = new bootstrap.Modal("#modal-no-crypto");
        oops.show();
    }

    // Force disable DOM Elements
    module_unavailable() {
        document.getElementById("encrypt-and-send").disabled = true;
        document.getElementById("message").disabled = true;
        this.modal_crypto_failed();
    }

    // Ensure module Crypto is accessible
    check_availidity() {
        return (window.crypto.subtle !== undefined);
    }

    notification_trigger(content, timeout) {
        const live = document.getElementById("live-notifier");
        const tolive = new bootstrap.Toast(live, {"delay": timeout});

        live.querySelector(".toast-body").innerText = content;
        tolive.show();
    }
}

// Main instance of Msgur
const msgur = new SecureMessenger();

document.addEventListener("DOMContentLoaded", (event) => {
    if(!msgur.check_availidity()) {
        return msgur.module_unavailable();
    }

    const kntxt = {
        id: window.location.pathname.substr(1),
        key: window.location.hash.substr(1),
    };

    if(kntxt.id && kntxt.key) {
        return msgur.request_message(kntxt).then(
            (response) => {
                document.getElementById("fetch-ready").classList.remove("d-none");
            },
            (reason) => {
                msgur.show_error_message(reason);
            }
        );
    }

    return msgur.initialize_editor();
});
