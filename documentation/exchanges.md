# what is hidden, what is visible?
first exchange for a new user is made via RSA, the rest is done via AES; all communication is encrypted somehow.

- usernames in chatroom: visible
- bid for auction: visible
- username in auction before end: hidden (maybe hashed?)
- username in auction after end: visible
- passwords: stored as hashed

# protocol
## server (startup)
gen RSA keypair

## client (startup + contacting)
gen RSA keypair
gen AES key
get server public RSA key
`HELLO <AES key>`
= (sign + encrypt AES key using RSA
send encrypted AES key to server)

## server (contacted)
recieve message from client
decrypt + verify message using RSA
if verification fails:
    end communication with client
else:
    hash client AES key to use as user_id / user_name
    add client to clients
(opt: send confirmation to client using AES)

## client (send bid)
`BID <auction_id> <amount>`
= (send amount to server using AES)

## server (recieve bid)
if highest bid on auction_id < client bid:
    save new best bid for auction_id
    (opt: reply to client with confirmation using AES)
else:
    (opt: reply to client with error using AES)

## client (view auction)
ask server for details on auction auction_id

## server (requrest to view auction)
if timer at auction_id <= 0:
    reply with best bid by username
else:
    reply with best bid by anonymous user (AES)

## server (time on auction ended)
(opt: contact winning client for confirmation)
broadcast (AES) winning username and bid to all clients (opt: ... who participated in a given auction)

# vulnerabilites?
- brute force passwords or other clients' AES/RSA keys
- biclique attack (https://en.wikipedia.org/wiki/Biclique_attack) on the AES parts of the protocol. (only divides the time to search by 4 according to https://security.stackexchange.com/a/57531, making this weakness pretty inconsequential, so this attack is not relevant in practice).
- rainbow tables to brute-force client passwords (can be solved by appending a string at the end of a password).
- DDOS to prevent others' bids from going through (can be solved by introducing a timeout between messages to handle).
- fault-injection during the first part of the exchange (as seen in https://pablo.rauzy.name/teaching/is/09-canaux-auxiliaires.pdf). (python secretly does a lot of things under the hood so side-channel attacks are in practice more difficult to do, probably not expected to happen).
- quantum-attack because regular RSA and AES are theoretically quantum-vulnerable (can be solved by using one of the last-round contestants of the algorithms listed here https://www.youtube.com/watch?v=aw6J1JV_5Ec). (though no quantum-computer powerful enough exists yet, and obviously we at Paris 8 do not have access to a quantum-computer).
