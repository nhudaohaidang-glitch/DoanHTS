/* =============================================================================
 * libc_min.c - memset/memcpy toi thieu: trinh bien dich co the tu goi cac ham nay
 * khi khoi tao mang/struct, ma firmware khong lien ket thu vien C chuan.
 * ========================================================================== */
#include <stddef.h>

void *memset(void *d, int c, size_t n)
{
    unsigned char *p = d;
    while (n--)
        *p++ = (unsigned char)c;
    return d;
}

void *memcpy(void *d, const void *s, size_t n)
{
    unsigned char *p = d;
    const unsigned char *q = s;
    while (n--)
        *p++ = *q++;
    return d;
}
