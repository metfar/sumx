answer = "N"

DEFINE WINDOW wDialogo \
    FROM 4, 10 TO 12, 55 \
    TITLE " Confirmación " \
    SHADOW \
    PANEL \
    COLOR SCHEME 5

ACTIVATE WINDOW wDialogo
@ 1, 2 SAY "¿Desea continuar?"
@ 3, 2 GET answer PICTURE "@!" VALID ValidarRespuesta(answer)
READ
DEACTIVATE WINDOW wDialogo
RELEASE WINDOW wDialogo

? "Respuesta: " + answer

FUNCTION ValidarRespuesta
    PARAMETER cValor
    IF NOT (cValor $ "SN")
        = MESSAGEBOX("¡Atención! Solo se permite 'S' o 'N'.", 48, " Error ")
        RETURN FALSE
    ENDIF
    RETURN TRUE
