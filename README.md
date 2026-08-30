# Messenger Secure (msgur)

In summary, this web service provide a way to host a message in a secure way, only
readable one time, destroyed on read. Message are encrypted and no-one except the
first one with the url can read it.

# Technical details
Message are encrypted using AES algorythm. The encryption key is never sent to the server (client-side generated)
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

This documents will receive some updates the next few days related to implementation changes.

# Database Schema

```sql
-- Table Structure
CREATE TABLE messages (
  id varchar(12) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
  ciphertext text CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
  created timestamp NOT NULL DEFAULT current_timestamp(),
  seen timestamp NULL DEFAULT NULL,
  iv varchar(24) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- Indexes
ALTER TABLE messages ADD PRIMARY KEY (id), ADD KEY seen (seen);
```
