CC = gcc
CFLAGS = -Wall -Wextra -g

UTILS_OBJ = utils.o

.PHONY: all clean

all: clean server client

# Serveur Python : on copie le script et on le rend exécutable
server: server.py
	@cp $< $@
	@chmod +x $@

# Client C : toujours compilé avec utils.o
#$(UTILS_OBJ): utils.c protocole.h
#	$(CC) $(CFLAGS) -c $< -o $@

#client: client.c $(UTILS_OBJ) protocole.h
#	$(CC) $(CFLAGS) client.c $(UTILS_OBJ) -o $@

# Client Python : on copie le script et on le rend exécutable
client: client.py
	@cp $< $@
	@chmod +x $@


clean:
	rm -f server client $(UTILS_OBJ)
#	rm -r __pycache__/
