CC = gcc
CFLAGS = -Wall -Wextra -g

UTILS_OBJ = utils.o

.PHONY: all clean

all: clean server client

# Serveur Python : on copie le script et on le rend exécutable
server: server.py
	@cp $< $@
	@chmod +x $@

# Client Python : on copie le script et on le rend exécutable
client: client.py
	@cp $< $@
	@chmod +x $@


clean:
	rm -f server client $(UTILS_OBJ)
#	rm -r __pycache__/
