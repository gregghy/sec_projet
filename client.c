#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdarg.h>

#define MAX_PSEUDO 16
#define MAX_LINE 256

static int connect_to(const char *host, const char *port) {
    struct addrinfo hints = {
        .ai_family = AF_UNSPEC,
        .ai_socktype = SOCK_STREAM
    }, *res;
    
    if (getaddrinfo(host, port, &hints, &res)) {
        perror("getaddrinfo");
        return -1;
    }
    
    int fd = socket(res->ai_family, res->ai_socktype, 0);
    if (fd < 0) {
        perror("socket");
        freeaddrinfo(res);
        return -1;
    }
    
    if (connect(fd, res->ai_addr, res->ai_addrlen) < 0) {
        perror("connect");
        close(fd);
        freeaddrinfo(res);
        return -1;
    }
    
    freeaddrinfo(res);
    return fd;
}

static int send_line(int fd, const char *fmt, ...) {
    char buf[MAX_LINE];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf) - 1, fmt, ap);
    va_end(ap);
    
    strcat(buf, "\n");
    return write(fd, buf, strlen(buf));
}

static int read_line(int fd, char *buf, size_t size) {
    size_t i = 0;
    while (i < size - 1) {
        int n = read(fd, buf + i, 1);
        if (n <= 0) return n;
        if (buf[i] == '\n') {
            buf[i] = '\0';
            return i;
        }
        i++;
    }
    buf[i] = '\0';
    return i;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <host> <port>\n", argv[0]);
        return 1;
    }
    
    // Connexion au serveur
    int fd = connect_to(argv[1], argv[2]);
    if (fd < 0)
        return 1;
    
    printf("Connecté à %s:%s\n", argv[1], argv[2]);
    
    // Lecture du message de bienvenue
    char buf[MAX_LINE];
    if (read_line(fd, buf, sizeof(buf)) > 0) {
        printf("%s\n", buf);
    }
    
    // Demande du pseudo
    char pseudo[MAX_PSEUDO];
    printf("Entrez un pseudo : ");
    fflush(stdout);
    if (!fgets(pseudo, sizeof(pseudo), stdin)) {
        fprintf(stderr, "Erreur lecture pseudo\n");
        close(fd);
        return 1;
    }
    pseudo[strcspn(pseudo, "\n")] = '\0';
    
    // Envoi de l'authentification
    send_line(fd, "HELLO %s", pseudo);
    
    // Boucle principale
    fd_set fds;
    while (1) {
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        FD_SET(fd, &fds);
        
        if (select(fd + 1, &fds, NULL, NULL, NULL) < 0) {
            perror("select");
            break;
        }
        
        // Entrée utilisateur
        if (FD_ISSET(STDIN_FILENO, &fds)) {
            if (!fgets(buf, sizeof(buf), stdin))
                continue;
            buf[strcspn(buf, "\n")] = '\0';
            
            if (strlen(buf) > 0) {
                send_line(fd, "%s", buf);
            }
        }
        
        // Message du serveur
        if (FD_ISSET(fd, &fds)) {
            int n = read_line(fd, buf, sizeof(buf));
            if (n <= 0) {
                printf("Serveur déconnecté\n");
                break;
            }
            printf("%s\n", buf);
        }
    }
    
    close(fd);
    return 0;
}