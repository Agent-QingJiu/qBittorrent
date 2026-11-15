#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int credential(void)
{
    unsigned char random[24], salt[16], hash[64], salt64[25], hash64[89];
    char password[49];
    if (RAND_bytes(random, sizeof random) != 1 || RAND_bytes(salt, sizeof salt) != 1)
        return 1;
    for (size_t i = 0; i < sizeof random; ++i)
        snprintf(password + 2 * i, 3, "%02x", random[i]);
    if (PKCS5_PBKDF2_HMAC(password, strlen(password), salt, sizeof salt,
                          100000, EVP_sha512(), sizeof hash, hash) != 1)
        return 1;
    EVP_EncodeBlock(salt64, salt, sizeof salt);
    EVP_EncodeBlock(hash64, hash, sizeof hash);
    return printf("%s\n%s:%s\n", password, salt64, hash64) < 0 || fflush(stdout) == EOF;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "credential") == 0)
        return credential();
    if (argc != 6 || strcmp(argv[1], "run") != 0)
        return 2;

    const struct passwd *account = getpwnam(argv[2]);
    if (!account || account->pw_uid == 0)
        return 1;
    const uid_t uid = account->pw_uid;
    const gid_t gid = account->pw_gid;
    if (setsid() < 0 || initgroups(argv[2], gid) < 0 ||
        setgid(gid) < 0 || setuid(uid) < 0)
        goto error;

    umask(0077);
    if (chdir(argv[3]) < 0 || clearenv() < 0 ||
        setenv("HOME", argv[3], 1) < 0 || setenv("PATH", "/usr/bin:/bin", 1) < 0 ||
        setenv("LANG", "C.UTF-8", 1) < 0)
        goto error;
    int log = open(argv[4], O_WRONLY | O_CREAT | O_APPEND | O_NOFOLLOW, 0600);
    if (log < 0 || dup2(log, STDOUT_FILENO) < 0 || dup2(log, STDERR_FILENO) < 0)
        goto error;
    if (log > STDERR_FILENO)
        close(log);
    execl(argv[5], argv[5], "--profile", argv[3], (char *)NULL);
error:
    perror("qbt-service");
    return 1;
}
