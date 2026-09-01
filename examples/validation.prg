answer = "N"

@ 1, 2 SAY "¿Desea continuar?"
@ 3, 2 GET answer PICTURE "@!" \
    VALID answer $ "SN" \
    ERROR "Opción inválida. Presione 'S' para Sí o 'N' para No."
READ

? "Respuesta: " + answer
