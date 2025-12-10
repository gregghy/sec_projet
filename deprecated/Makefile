CC = gcc
CFLAGS = -Wall -Wextra -g

.PHONY: all clean

all: clean server client audit_client

# Serveur Python : on copie le script et on le rend exécutable
server: server.py
	@cp $< $@
	@chmod +x $@

# Client Python : on copie le script et on le rend exécutable
client: client.py
	@cp $< $@
	@chmod +x $@

audit_client: audit_client.py
	@cp $< $@
	@chmod +x $@


clean:
	rm -f server client audit_client $(UTILS_OBJ)

clean_pycache:
	rm -r __pycache__/
