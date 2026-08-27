answer = "N"

DEFINE WINDOW wDialogo \
    FROM 4, 10 TO 12, 55 \
    TITLE " Confirmación " \
    SHADOW \
    PANEL \
    COLOR SCHEME 5

ACTIVATE WINDOW wDialogo
@ 1, 2 PRINT "¿Desea continuar?"
@ 3, 2 GET answer WIDTH 1 PICTURE "@! A"
READ
DEACTIVATE WINDOW wDialogo
RELEASE WINDOW wDialogo

PRINT "Respuesta: " + answer
