# tp-docker-dns
# TP Entorno de Red con Pi-hole y Unbound
# Malena Zurita y Lucas Viviani

## 1. Propósito y Descripción General
Este proyecto implementa una infraestructura DNS privada y reproducible utilizando Docker y Docker Compose. 
El objetivo es proporcionar un servicio DNS seguro que:
* Filtre publicidad y rastreadores: Respondiendo `0.0.0.0` a dominios maliciosos o publicitarios mediante Pi-hole.
* Resuelva de forma recursiva: Consultando directamente a los servidores raíz de Internet a través de Unbound (sin reenviar peticiones a proveedores externos como Google o Cloudflare).
* Valide autenticidad: Verificando las firmas criptográficas mediante DNSSEC.
* Monitoree métricas: Exponiendo un dashboard minimalista desarrollado a medida (Reporter) que consume la API de Pi-hole.

---

## 2. Arquitectura de Servicios

```text
                               ┌────────────────────────────────────────────────────────────┐
                               │                     RED DOCKER: dns-net                    │
                               │                                                            │
[ Cliente / Browser ] ───────► │   ┌──────────────┐            ┌────────────────────────┐   │        ┌────────────────────────┐
   Port 8080 (GUI Web)         │   │   Pi-hole    │ ─────────► │ Unbound (mvance)       │   │ ─────► │ Servidores DNS Raíz    │
   Port 53 (DNS Query)         │   │  (DNS+API)   │   p5335    │ (DNSSEC / Recursivo)   │   │        │ (. / .com / etc.)      │
                               │   └──────────────┘            └────────────────────────┘   │        └────────────────────────┘
                               │          ▲                                                 │
[ Browser / Monitor ] ────────►│   ┌──────┴───────┐                                         │
   Port 8081 (Reportes)        │   │   Reporter   │                                         │
                               │   └──────────────┘                                         │
                               └────────────────────────────────────────────────────────────┘


## 3. Prerrequisitos y preparacion del Host
Antes de desplegar los contenedores en Ubuntu/Debian, es necesario liberar el puerto 53 que ocupa por defecto el servicio systemd-resolved:
Bash
    # 1. Desactivar el Stub Listener de systemd-resolved
         sudo sed -i 's/^#\?DNSStubListener=.*/DNSStubListener=no/' /etc/systemd/resolved.conf

    # 2. Apuntar resolv.conf directamente al DNS del sistema
         sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf

    # 3. Reiniciar el servicio
         sudo systemctl restart systemd-resolved

    # 4. Verificar que el puerto 53 esté libre (no debe devolver resultados)
         sudo ss -tulpn | grep -E ':53[[:space:]]'

## 4. Despliegue de infraestructura
    # 1. Clonar el repositorio
            git clone [https://github.com/luxius81/tp-docker-dns.git](https://github.com/luxius81/tp-docker-dns.git)
            cd tp-docker-dns

    # 2. Configurar las variables de entorno
            cp .env.example .env

    # (Opcional) Editar el archivo .env para modificar la contraseña de la API
            nano .env

    # 3. Levantar los servicios con Docker Compose
           sudo docker compose up -d

## 5. Accesos y Paneles Web
        Interfaz de Pi-hole: http://localhost:8080/admin (Contraseña configurada en .env)

        Dashboard del Reporter: http://localhost:8081

## 6. PLan de pruebas y verificacion
    # 1. Resolución y Validación DNSSEC en Unbound
            # Prueba 1: Dominio legítimo con firma DNSSEC válida (Debe responder NOERROR y mostrar el flag 'ad')
                dig dnssec.works @127.0.0.1 -p 5335 +dnssec

            # Prueba 2: Dominio con firma DNSSEC alterada/inválida (Debe responder SERVFAIL)
                dig fail01.dnssec.works @127.0.0.1 -p 5335

    # 2. Bloqueo y Resolución en Pi-hole
            # Prueba 1: Dominio de publicidad (Debe responder 0.0.0.0)
                dig doubleclick.net @127.0.0.1

            # Prueba 2: Dominio legítimo (Debe devolver la IP real)
                dig debian.org @127.0.0.1

## 7. Configurar Ubuntu y navegadores para usar Pi-hole

El sistema operativo utiliza los servidores DNS asignados automáticamente por el router o el proveedor de internet (ISP). Para darle un uso real y cotidiano es necesario redirigir las consultas DNS de todo el sistema hacia nuestra instancia local.

Para que todas las aplicaciones del sistema operativo resuelvan nombres de dominio a través de Pi-hole:

1. Abrí la Configuración de red en Ubuntu
2. Hacé clic en el ícono del engranaje junto a tu conexión activa.
3. Ingresá a la pestaña IPv4.
4. En el apartado DNS, desactivá el interruptor Automático para evitar que el DHCP del router sobrescriba la configuración.
5. En el campo de texto Servidores DNS, ingresá la dirección local:
   127.0.0.1
6. En el navegador (Firefox, Chrome) segurarse de tener desactivado DNS sobre HTTPS (DoH)

## 8. Detencion y limpieza
Para detener la infraestructura y limpiar los recursos generados:
    # Detener los contenedores y remover la red interna
        sudo docker compose down

    # Eliminar imágenes locales generadas (incluyendo la del Reporter)
        sudo docker compose down --rmi local

    # Borrar la carpeta de datos persistentes de Pi-hole (requiere sudo por permisos de Docker)
        sudo rm -rf etc-pihole
