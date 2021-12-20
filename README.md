# Messenger Secure (msgur)

In summary, this web-service provide a way to host a message in a secure way, only
readable one time, destructed when read. Message are encrypted and no-one except the
first one with the url can read it.

# Technical details
Message are encrypted using AES algorythm. The cipher key is never sent to the server (client-side generated)
and the client generate the url. The server doesn't know the key and never receive it.

Workflow:
- The user write his message, then clic on "Encrypt and Send" button
- A key (uuid4) is generated, client-side (in the browser)
- The message is encrypted using that key (client-side in the browser)
- The encrypted message (and nothing else) is sent to the server to store it
- The server reply with a unique id matching with the message
- The reader URL is generated (client-side in the browser) using the returned id and the key

You need to know the `id` and the `key` to get the message and decrypt it.

The server doesn't know the key, it's not possible for anyone who have access to the server to decrypt
a message without the key, even the administrator. The key is only available to the creator, on his browser.

When a request to the message is made, the message is deleted from the database, permanently.
