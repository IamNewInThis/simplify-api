# Simplify API

Backend FastAPI para la plataforma Simplify.

## 📋 Descripción

Este servicio proporciona la API REST que conecta el frontend con el motor de scraping y el servicio de IA. Gestiona autenticación, encolamiento de tareas, y almacenamiento de datos.

## 🏗️ Estructura del Proyecto

```
simplify-api/
├── app/
│   ├── api/                # Endpoints REST
│   ├── models/             # Modelos de base de datos (SQLAlchemy)
│   ├── schemas/            # Schemas de validación (Pydantic)
│   ├── services/           # Lógica de negocio
│   ├── core/               # Configuración y seguridad
│   └── main.py             # Entry point de FastAPI
├── alembic/                # Migraciones de base de datos
├── venv/                   # Entorno virtual (no se versiona)
├── requirements.txt        # Dependencias de Python
├── .env.example            # Ejemplo de variables de entorno
└── README.md               # Este archivo
```

## 🛠️ Tecnologías

- **FastAPI** - Framework web de alto rendimiento
- **SQLAlchemy** - ORM para PostgreSQL
- **Alembic** - Migraciones de base de datos
- **Pydantic** - Validación de datos
- **Celery** - Encolamiento de tareas
- **Redis** - Cache y message broker
- **JWT** - Autenticación

## ⚙️ Instalación

### 1. Crear y activar entorno virtual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

### 4. Ejecutar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 --reload
```

El servidor estará disponible en: `http://localhost:8080`

Documentación interactiva: `http://localhost:8080/docs`

## 📦 Gestión de Dependencias

### Congelar versiones instaladas

Después de instalar nuevas librerías, congela las versiones exactas:

```bash
pip freeze > requirements.txt
```

### Instalar una nueva librería

```bash
# Activar entorno virtual primero
source venv/bin/activate

# Instalar librería
pip install nombre-libreria

# Congelar versiones actualizadas
pip freeze > requirements.txt
```

## 🚀 Uso

### Activar entorno virtual

Siempre que trabajes en este proyecto, activa primero el entorno virtual:

```bash
source venv/bin/activate
```

### Ejecutar en modo desarrollo

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Desactivar entorno virtual

```bash
deactivate
```

## 🗄️ Base de Datos

### Crear migraciones con Alembic

```bash
# Generar nueva migración
alembic revision --autogenerate -m "descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir migración
alembic downgrade -1
```

## 📝 Endpoints Disponibles

- `GET /` - Información de la API
- `GET /health` - Health check
- `GET /docs` - Documentación interactiva (Swagger)
- `GET /redoc` - Documentación alternativa (ReDoc)

## 📝 Próximos Pasos

- Implementar autenticación JWT
- Crear endpoints de usuarios
- Configurar base de datos PostgreSQL
- Implementar encolamiento con Celery
- Crear endpoints de scraping
- Añadir logging y monitoreo

## 🔗 Servicios Relacionados

- [simplify-frontend](../simplify-frontend/) - Interfaz de usuario
- [simplify-scraper](../simplify-scraper/) - Motor de scraping
- [simplify-ai-service](../simplify-ai-service/) - Servicio de normalización con IA
