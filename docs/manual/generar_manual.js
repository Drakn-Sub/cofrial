const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  HeadingLevel, AlignmentType, LevelFormat, BorderStyle, TableOfContents, PageBreak, Footer, Header,
  PageNumber, TabStopType,
} = require("docx");

const SP = "/tmp/claude-0/-home-claude/c68bf61e-dff4-59eb-bc1b-42978b64b0a5/scratchpad";
const M = path.join(SP, "manual");
const EV = "/home/claude/cofrial/docs/evidencias/04-plataforma";
const OUT = path.join(SP, "Manual_de_uso_Cofrial.docx");

const PIZARRA = "17242C", GLACIAR = "2D6A97", NIEBLA = "5B6D78", TEMPLE = "2F8A72", RUPTURA = "C43D2B";
const ANCHO = 9638; // A4 con márgenes de 2 cm (11906 - 2*1134)

const t = (text, o = {}) => new TextRun({ text, ...o });
const p = (runs, o = {}) => new Paragraph({ children: Array.isArray(runs) ? runs : [t(runs)], spacing: { after: 120 }, ...o });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)], pageBreakBefore: true });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(text)] });
const h3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [t(text)] });
const punto = (runs) => new Paragraph({ numbering: { reference: "puntos", level: 0 }, children: Array.isArray(runs) ? runs : [t(runs)], spacing: { after: 60 } });
const paso = (ref, runs) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: Array.isArray(runs) ? runs : [t(runs)], spacing: { after: 60 } });
const b = (text) => t(text, { bold: true });

function imagen(archivo, pie, ancho = 620) {
  const ruta = fs.existsSync(path.join(M, archivo)) ? path.join(M, archivo) : path.join(EV, archivo);
  const datos = fs.readFileSync(ruta);
  // tamaño real para conservar la proporción
  let w, h;
  if (ruta.endsWith(".png")) { w = datos.readUInt32BE(16); h = datos.readUInt32BE(20); }
  else { // JPEG: buscar marcador SOF
    let i = 2; while (i < datos.length) { const m = datos[i + 1]; const len = datos.readUInt16BE(i + 2);
      if (m >= 0xc0 && m <= 0xc3) { h = datos.readUInt16BE(i + 5); w = datos.readUInt16BE(i + 7); break; } i += 2 + len; } }
  const alto = Math.round(ancho * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: ruta.endsWith(".png") ? "png" : "jpg", data: datos, transformation: { width: ancho, height: alto },
        altText: { title: pie, description: pie, name: archivo } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [t(pie, { italics: true, size: 18, color: NIEBLA })] }),
  ];
}

function tabla(encabezados, filas, anchos) {
  const borde = { style: BorderStyle.SINGLE, size: 4, color: "C7D4DB" };
  const bordes = { top: borde, bottom: borde, left: borde, right: borde };
  const celda = (texto, i, cabecera) => new TableCell({
    width: { size: anchos[i], type: WidthType.DXA }, borders: bordes,
    shading: cabecera ? { fill: "E6EFF4", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: (Array.isArray(texto) ? texto : [texto]).map((x) => new Paragraph({ children: [t(x, { bold: !!cabecera, size: 19 })] })),
  });
  return new Table({
    width: { size: anchos.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: anchos,
    rows: [new TableRow({ tableHeader: true, children: encabezados.map((x, i) => celda(x, i, true)) }),
      ...filas.map((f) => new TableRow({ children: f.map((x, i) => celda(x, i, false)) }))],
  });
}

function nota(titulo, texto, color = GLACIAR) {
  return new Paragraph({
    spacing: { before: 120, after: 160 }, indent: { left: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color, space: 10 } },
    children: [b(titulo + " "), t(texto)],
  });
}

// Bloque estándar de cada pantalla
function pantalla({ titulo, imagenArchivo, pie, direccion, quien, para, pasos, detras, ref }) {
  const out = [h2(titulo)];
  if (direccion) out.push(p([b("Dónde: "), t(direccion, { color: GLACIAR })], { keepNext: true }));
  if (quien) out.push(p([b("Quién la usa: "), t(quien)], { keepNext: true }));
  if (imagenArchivo) out.push(...imagen(imagenArchivo, pie));
  out.push(h3("Para qué sirve"), p(para));
  if (pasos) { out.push(h3("Cómo se usa")); pasos.forEach((x) => out.push(paso(ref, x))); }
  if (detras) { out.push(h3("Qué pasa por detrás")); detras.forEach((x) => out.push(punto(x))); }
  return out;
}

let n = 0; const lista = () => `pasos${++n}`;
const listas = [];
function L() { const r = lista(); listas.push(r); return r; }

const contenido = [];

// ---------- Portada ----------
contenido.push(
  new Paragraph({ spacing: { before: 2400 }, children: [t("Cofrial SpA", { size: 30, color: GLACIAR, bold: true })] }),
  new Paragraph({ heading: HeadingLevel.TITLE, children: [t("Manual de uso del sistema")] }),
  p([t("Tienda en línea, CRM, torre de control IoT, panel de pedidos y dashboard gerencial: qué hace cada pantalla y cómo se usa.", { size: 26, color: NIEBLA })], { spacing: { after: 600 } }),
  new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 24, color: GLACIAR, space: 1 } }, children: [] }),
  p([b("Equipo: "), t("Benjamín Aguilar y Daniel Jara")]),
  p([b("Asignatura: "), t("Transformación Digital (TIEL15), INACAP Sede Temuco")]),
  p([b("Versión: "), t("1.1, noviembre de 2026")]),
  p([t("Todos los clientes, personas, RUT y pedidos que aparecen en las imágenes son ficticios.", { italics: true, color: NIEBLA, size: 19 })], { spacing: { before: 600 } }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t("Contenido")] }),
  new TableOfContents("Contenido", { hyperlink: true, headingStyleRange: "1-2" }),
);

// ---------- 1. Cómo está organizado ----------
contenido.push(
  h1("1. Cómo está organizado el sistema"),
  p("Cofrial tiene cinco pantallas principales. Todas leen y escriben en la misma base de datos, por eso lo que pasa en una se ve de inmediato en las otras: un pedido de la tienda aparece en el CRM y en el panel de pedidos, y una falla de frío en un camión cambia el estado de los pedidos que lleva."),
  tabla(["Pantalla", "Dirección", "Quién la usa", "Para qué"], [
    ["Tienda", "tienda.cofrial-temuco.duckdns.org", "Público e instituciones con convenio", "Ver productos, comprar y seguir pedidos"],
    ["Intranet: Ventas (CRM)", "crm.cofrial-temuco.duckdns.org", "Ventas y jefatura comercial", "Seguir oportunidades de venta y reclamos"],
    ["Intranet: Torre de control", "ops.cofrial-temuco.duckdns.org", "Despacho", "Ver la flota en vivo y atender alertas de frío"],
    ["Intranet: Pedidos y catálogo", "Menú de la intranet", "Despacho y jefatura", "Gestionar pedidos, productos y stock"],
    ["Intranet: Administración", "Menú de la intranet", "Administrador", "Usuarios, clientes, registros y auditoría"],
    ["Dashboard gerencial", "bi.cofrial-temuco.duckdns.org", "Gerencia", "Indicadores de ventas y cadena de frío"],
  ], [1700, 3000, 2300, 2638]),
  p("Hay tres ingresos distintos: el de la tienda (clientes), el de la intranet (personal) y el de Metabase (gerencia). Las direcciones crm. y ops. llevan a la misma intranet: después de iniciar sesión, cada persona llega a la pantalla de su rol."),
  nota("Por seguridad:", "las pantallas internas y el ingreso del personal no existen en la dirección de la tienda. Si alguien escribe tienda…/admin/ recibe un error 404."),
  h2("Usuarios de prueba"),
  tabla(["Usuario", "Rol", "Qué puede hacer"], [
    ["compras@hospital-demo.cl", "Cliente con convenio (B2B)", "Comprar en la tienda con los precios de su convenio y ver sus pedidos"],
    ["vendedor@cofrial.cl", "Ventas", "CRM (solo sus oportunidades) y fichas de prospectos y mensajes"],
    ["despacho@cofrial.cl", "Despacho", "Torre de control, pedidos y fichas de camiones y despachos"],
    ["jefatura@cofrial.cl", "Jefatura comercial", "CRM completo, pedidos y fichas de clientes"],
    ["benjamin", "Administrador", "Todo, incluidos los usuarios y la auditoría"],
  ], [2900, 2300, 4438]),
  p([t("Las contraseñas no están escritas en este manual. Las define el equipo con el comando changepassword en el servidor; jefatura@cofrial.cl todavía no tiene una.", { italics: true, color: NIEBLA })]),
);

// ---------- 2. Tienda ----------
contenido.push(h1("2. Tienda en línea"),
  p("La tienda es la cara pública de Cofrial. Reemplaza los pedidos por teléfono, correo y WhatsApp: el cliente elige, paga y sigue su pedido sin llamar a nadie."));
contenido.push(...pantalla({ titulo: "2.1 Catálogo de productos", imagenArchivo: "01_tienda_catalogo.png", pie: "Catálogo con los productos congelados y refrigerados",
  direccion: "https://tienda.cofrial-temuco.duckdns.org/catalogue/", quien: "Cualquier visitante, con o sin cuenta.",
  para: "Muestra los 20 productos disponibles con su foto, precio y si hay stock. El sello de cada foto indica la temperatura a la que viaja el producto: −18 °C los congelados y 0 a 4 °C los refrigerados.",
  ref: L(), pasos: ["Usa la lista de la izquierda para filtrar por Congelados o Refrigerados.", "Escribe en Buscar para encontrar un producto por su nombre.", "Haz clic en la foto o el nombre para ver la ficha completa, o en Añadir al carrito para comprarlo directamente."],
  detras: ["Los productos, precios y stock se leen en vivo desde la base de datos en Amazon RDS.", "Las fotos están en un almacenamiento privado (Amazon S3) y se entregan con enlaces que caducan en una hora."] }));
contenido.push(...pantalla({ titulo: "2.2 Ficha de producto y precio de convenio", imagenArchivo: "02_tienda_producto_publico.png", pie: "Ficha vista por el público: precio de catálogo $8.990",
  para: "Muestra la descripción, el stock y el precio. El precio cambia según quién está mirando: el público ve el precio de catálogo y una institución con convenio ve su precio rebajado.",
  ref: L(), pasos: ["Revisa la descripción y el stock disponible.", "Presiona Añadir al carrito."] }));
contenido.push(...imagen("05_tienda_producto_convenio.png", "El mismo producto visto por el Hospital Regional (cliente con convenio): $7.990"));
contenido.push(nota("Cómo funciona el convenio:", "cada institución tiene una lista de precios con fecha de vigencia. Al iniciar sesión, la tienda reconoce a qué institución pertenece el usuario y aplica esa lista. Si el convenio vence, vuelve al precio público sin que nadie tenga que cambiar nada."));
contenido.push(...pantalla({ titulo: "2.3 Carrito y compra", imagenArchivo: "03_tienda_carrito.png", pie: "Carrito con un producto agregado",
  direccion: "https://tienda.cofrial-temuco.duckdns.org/basket/",
  para: "Reúne los productos elegidos antes de pagar. Permite cambiar cantidades, quitar productos y ver el total.",
  ref: L(), pasos: ["Cambia la cantidad y presiona Actualizar, o usa Eliminar para quitar un producto.", "Presiona Ir a la caja para continuar.", "Inicia sesión (la tienda no acepta compras anónimas: todo pedido queda asociado a un cliente).", "Completa la dirección de despacho y confirma. La tienda muestra el número del pedido, por ejemplo D100215."],
  detras: ["El pedido nace con el estado Recibido.", "Si el cliente es una institución, el pedido queda registrado en su ficha del CRM para que el vendedor lo vea.", "La creación del pedido queda en el registro de auditoría."] }));
contenido.push(...pantalla({ titulo: "2.4 Ingreso y registro", imagenArchivo: "04_tienda_ingreso.png", pie: "Formularios para iniciar sesión o crear una cuenta",
  direccion: "https://tienda.cofrial-temuco.duckdns.org/accounts/login/",
  para: "Permite iniciar sesión a los clientes que ya tienen cuenta y crear una cuenta nueva al público general.",
  detras: ["Las contraseñas se guardan cifradas con Argon2, nunca en texto legible.", "Después de 5 intentos fallidos, el acceso se bloquea por una hora para ese usuario y esa conexión. Esto frena a quien intente adivinar contraseñas."] }));
contenido.push(...pantalla({ titulo: "2.5 Mis pedidos", imagenArchivo: "06_tienda_mis_pedidos.png", pie: "Historial de pedidos del cliente",
  direccion: "Menú Cuenta → Historial de pedidos",
  para: "El cliente ve todos sus pedidos y su estado actual: Recibido, Pagado, En preparación, Asignado, En ruta, En ruta con alerta, Entregado, Rechazado o Anulado.",
  detras: ["Cada cliente ve solo sus propios pedidos. Si cambia el número en la dirección para mirar el pedido de otro, recibe un error 404."] }));

// ---------- 3. Intranet ----------
contenido.push(h1("3. Intranet: ingreso, roles y navegación"),
  p("La intranet agrupa las herramientas del personal: CRM, torre de control, pedidos y administración. Tiene un solo ingreso y cada persona ve únicamente lo que corresponde a su rol."));
contenido.push(...pantalla({ titulo: "3.1 Ingreso a la intranet", imagenArchivo: "07b_ingreso.png", pie: "Ingreso único del personal",
  direccion: "https://crm.cofrial-temuco.duckdns.org o https://ops.cofrial-temuco.duckdns.org (ambas llevan al mismo ingreso)", quien: "Todo el personal.",
  para: "Es la única puerta de entrada del personal. Después de la contraseña y del código del celular, el sistema lleva a cada persona a la pantalla de su trabajo: ventas llega al embudo comercial, despacho a la torre de control.",
  detras: ["Después de 5 intentos fallidos el acceso se bloquea por una hora.", "Un cliente de la tienda que pruebe una dirección interna recibe un error 404, como si no existiera."] }));
contenido.push(...pantalla({ titulo: "3.2 Verificación en dos pasos", imagenArchivo: "07_intranet_2fa.png", pie: "La primera vez se activa el segundo factor escaneando el código QR",
  quien: "Todo el personal interno, cada vez que inicia sesión.",
  para: "Agrega una segunda llave además de la contraseña: un código de 6 dígitos que cambia cada 30 segundos en el celular del trabajador. Aunque alguien robe la contraseña, no puede entrar sin el celular. Hasta pasar este paso no se muestra ningún menú.",
  ref: L(), pasos: ["Inicia sesión con tu correo y contraseña.", "La primera vez aparece un código QR: escanéalo con Google Authenticator o Microsoft Authenticator.", "Escribe los 6 dígitos que muestra la aplicación y presiona Verificar.", "Las siguientes veces solo se pide el código."] }));
contenido.push(h2("3.3 Volver a escanear el código QR"),
  p("Si cambiaste de teléfono o quieres vincular otra aplicación de autenticación:"),
  paso(L(), "Inicia sesión normalmente, con el código de tu celular actual."),
  paso(listas[listas.length - 1], "En el menú lateral, abajo, presiona Vincular otro celular."),
  paso(listas[listas.length - 1], "Presiona Mostrar un código QR nuevo. El código del celular anterior deja de servir."),
  paso(listas[listas.length - 1], "Escanea el QR nuevo y escribe los 6 dígitos."),
  nota("Si perdiste el celular:", "no puedes hacerlo tú, porque el sistema exige el código actual para cambiarlo. El administrador lo reinicia en el servidor con: python manage.py reiniciar_2fa tu-correo. La próxima vez que entres verás un QR nuevo. Ambos casos quedan en la auditoría.", RUPTURA));
contenido.push(h2("3.4 El menú lateral y los roles"),
  p("Todas las pantallas internas tienen el mismo menú a la izquierda. El menú muestra solo las secciones que el rol puede abrir, y el rol aparece bajo el correo de la persona conectada."),
  tabla(["Rol", "Secciones que ve", "Pantalla de inicio"], [
    ["Ventas", "Ventas (CRM); Prospectos y mensajes", "Embudo comercial"],
    ["Despacho", "Torre de control; Pedidos y catálogo; Camiones y despachos", "Torre de control"],
    ["Jefatura comercial", "Ventas (CRM); Pedidos y catálogo; Prospectos y mensajes", "Embudo comercial"],
    ["Administrador", "Todas, más Administración (usuarios, auditoría y bloqueos)", "Embudo comercial"],
  ], [2200, 4838, 2600]),
  ...imagen("08b_ventas_sin_acceso.png", "Una vendedora intentó abrir la torre de control: el sistema la devolvió a su sección con un aviso"),
  p("Si alguien escribe a mano la dirección de una sección que no le corresponde, el sistema lo devuelve a la suya y registra el intento en la auditoría como ACCESO_DENEGADO."),
  p("Abajo del menú están Cambiar contraseña, Vincular otro celular y Cerrar sesión. La franja de colores del borde (azul, verde y rojo) es la escala de temperatura que usa todo el sistema: azul para congelado, verde para refrigerado y rojo para fuera de rango."));

// ---------- 4. CRM ----------
contenido.push(h1("4. Ventas (CRM)"));
contenido.push(...pantalla({ titulo: "4.1 Embudo comercial", imagenArchivo: "08_crm_embudo.png", pie: "Embudo con las oportunidades por etapa y los reclamos urgentes arriba",
  direccion: "https://crm.cofrial-temuco.duckdns.org/crm/", quien: "Ventas (cada vendedor ve solo sus oportunidades) y jefatura comercial (ve todas).",
  para: "Reemplaza la cartera de clientes que cada vendedor llevaba en su celular. Cada tarjeta es una oportunidad de venta y cada columna una etapa: Prospecto, Contactado, Calificado, Propuesta, Negociación, Ganado y Perdido. Arriba aparecen los reclamos urgentes que la inteligencia artificial detectó en los mensajes de los clientes.",
  ref: L(), pasos: ["Revisa primero los reclamos urgentes del recuadro rojo.", "Para avanzar una oportunidad, elige la nueva etapa en su lista y presiona Mover.", "Para registrar un cliente potencial nuevo, presiona Nuevo prospecto.", "El encabezado de cada columna muestra cuántas oportunidades hay y el monto estimado."],
  detras: ["Cada cambio de etapa queda en la auditoría con el nombre de quien lo hizo.", "Un vendedor no puede mover la oportunidad de otro: el sistema responde 404."] }));
contenido.push(h2("4.2 Clasificación automática con inteligencia artificial"),
  p("Cuando se registra un mensaje de un cliente (correo, llamada o portal), el sistema lo envía a Google Gemini (plan gratuito), que lo clasifica en Reclamo, Cotización, Despacho, Facturación u Otro, con urgencia Alta, Media o Baja."),
  ...imagen("15_admin_nueva_interaccion.png", "Registro de un mensaje de cliente en Prospectos y mensajes → Interacciones → Añadir"),
  paso(L(), "En el menú, entra a Prospectos y mensajes (o Administración) → Interacciones → Añadir interacción."),
  paso(listas[listas.length - 1], "Elige el cliente, el canal (Correo, Teléfono, Portal o Reunión) y escribe el mensaje."),
  paso(listas[listas.length - 1], "Presiona Guardar. La categoría y la urgencia se completan solas."),
  nota("Cuidado de los datos:", "antes de enviar el texto a Gemini, el sistema borra RUT, correos y teléfonos. Si la IA no responde, el mensaje queda como Sin clasificar y el CRM sigue funcionando.", TEMPLE));

// ---------- 5. Torre ----------
contenido.push(h1("5. Torre de control IoT"));
contenido.push(...pantalla({ titulo: "5.1 Vista general", imagenArchivo: "09_torre_control.png", pie: "Torre de control: alerta activa de CF-027, mapa de la flota y termómetro por camión",
  direccion: "https://ops.cofrial-temuco.duckdns.org/ops/", quien: "Despachadores.",
  para: "Reemplaza los grupos de WhatsApp y las llamadas a los conductores. Muestra dónde está cada uno de los 50 camiones, a qué temperatura va su carga y si alguno perdió la cadena de frío. La página se actualiza sola cada 30 segundos.",
  detras: ["Cada camión envía cada 30 segundos su temperatura, posición, combustible y si está fuera de rango. En este prototipo los camiones son simulados con contenedores Docker en un servidor dedicado.", "Cada minuto el sistema revisa las dos últimas lecturas de cada camión. Si las dos están fuera de rango, abre una alerta. Se piden dos lecturas para no alarmar por un error aislado del sensor."] }));
contenido.push(h2("5.2 El mapa en 3D"),
  p("El mapa muestra la imagen satelital de La Araucanía con el relieve real del terreno y un camión en 3D por cada unidad, orientado hacia donde va. Los camiones congelados se ven en azul, los refrigerados en verde y los que están fuera de rango en rojo, con una etiqueta fija que indica su temperatura."),
  punto("Haz clic en un camión para ver su temperatura."),
  punto("Mantén Ctrl (o dos dedos en el celular) y arrastra para inclinar o girar el mapa; con Ctrl + rueda del mouse se acerca o aleja."),
  punto("Los botones de la esquina permiten acercar, alejar y volver a apuntar al norte."),
  nota("Si no aparece el mapa 3D:", "el sistema usa automáticamente un mapa 2D. Eso pasa si falta la clave de Mapbox o si el navegador no soporta gráficos 3D."));
contenido.push(h2("5.3 El termómetro de cada camión"),
  p("A la derecha, cada camión tiene una barra que funciona como termómetro:"),
  punto([b("La franja de color "), t("es el rango permitido para ese tipo de carga: −25 a −18 °C para congelados y 0 a 4 °C para refrigerados.")]),
  punto([b("La marca vertical "), t("es la temperatura actual. Si está dentro de la franja, la carga va bien.")]),
  punto([b("Si la marca sale de la franja, "), t("la fila se pinta de rojo y el camión sube al primer lugar de la lista.")]));
contenido.push(h2("5.4 Atender una alerta"),
  p("Cuando un camión pierde el frío, aparece arriba un recuadro rojo con el camión, la temperatura más alta registrada y los pedidos que lleva."),
  paso(L(), "Contacta al conductor y averigua qué pasó."),
  paso(listas[listas.length - 1], "Escribe en el campo lo que se hizo, por ejemplo: el conductor revisó el equipo de frío y cerró bien la puerta."),
  paso(listas[listas.length - 1], "Presiona Tomar la alerta. Queda registrado tu nombre como responsable."),
  paso(listas[listas.length - 1], "Cuando la temperatura vuelve a la normalidad por dos lecturas seguidas, la alerta se cierra sola y pasa a Últimas alertas cerradas."),
  nota("Lo que el sistema hace solo al abrir una alerta:", "cambia los pedidos de ese camión a En ruta con alerta, deja un aviso de urgencia alta en la ficha del cliente en el CRM y lo anota en la auditoría. Antes, Cofrial se enteraba de estas fallas horas después.", RUPTURA));

// ---------- 6. Pedidos ----------
contenido.push(h1("6. Pedidos y catálogo"),
  p("Es el panel de trastienda de la tienda (django-oscar). Se abre desde el menú Pedidos y catálogo."));
contenido.push(...pantalla({ titulo: "6.1 Inicio del panel", imagenArchivo: "10_panel_inicio.png", pie: "Resumen de pedidos, clientes y ventas de las últimas 24 horas",
  para: "Muestra de un vistazo cuántos pedidos y clientes nuevos hubo en las últimas 24 horas y el total vendido." }));
contenido.push(...pantalla({ titulo: "6.2 Lista de pedidos", imagenArchivo: "11_panel_pedidos.png", pie: "Todos los pedidos con su estado, cliente y fecha",
  para: "Lista todos los pedidos de la tienda. Permite buscar por número, filtrar por estado o fecha y descargar los seleccionados en una planilla CSV.",
  ref: L(), pasos: ["Escribe el número del pedido en Buscar, o usa Búsqueda avanzada para filtrar por estado, cliente o fecha.", "Presiona Vista para abrir un pedido."] }));
contenido.push(...pantalla({ titulo: "6.3 Detalle de un pedido", imagenArchivo: "12_panel_detalle_pedido.png", pie: "Pedido D100211 en estado En ruta con alerta",
  para: "Muestra el cliente, los productos, los montos y la historia del pedido. Desde aquí se cambia su estado a medida que avanza: de Pagado a En preparación, Asignado, En ruta y Entregado.",
  ref: L(), pasos: ["En la sección del estado, elige el nuevo estado y confirma.", "El sistema solo permite los cambios que tienen sentido: por ejemplo, un pedido Entregado no puede volver a En preparación."] }));
contenido.push(p([b("Otras secciones del panel: "), t("Catálogo (productos, categorías y stock), Clientes, Ofertas y Reportes.")]));

// ---------- 7. Administración ----------
contenido.push(h1("7. Administración: fichas y registros"),
  p("Son las fichas de datos del sistema. El administrador las ve todas desde el menú Administración; ventas y despacho ven solo las suyas (Prospectos y mensajes, Camiones y despachos). Las tablas técnicas de la tienda no aparecen aquí: se gestionan en Pedidos y catálogo."));
contenido.push(...imagen("13_admin_inicio.png", "Fichas y registros vistos por el administrador"));
contenido.push(...pantalla({ titulo: "7.1 Clientes", imagenArchivo: "16_admin_clientes.png", pie: "Instituciones con convenio y su lista de precios",
  direccion: "Administración → Clientes",
  para: "Registro de cada institución o persona: RUT, razón social, comuna, condición de pago, lista de precios y si dio su consentimiento para el uso de sus datos (Ley 21.719)." }));
contenido.push(...pantalla({ titulo: "7.2 Prospectos", imagenArchivo: "18_admin_prospectos.png", pie: "Empresas interesadas que todavía no son clientes",
  direccion: "Administración → Prospectos",
  para: "Lista de empresas interesadas. Cuando un prospecto firma, se selecciona y se usa la acción Convertir en cliente B2B: el sistema crea el cliente con sus datos y lo deja listo para asignarle un convenio." }));
contenido.push(...pantalla({ titulo: "7.3 Interacciones", imagenArchivo: "14_admin_interacciones.png", pie: "Mensajes de clientes con la categoría y urgencia asignadas por la IA",
  direccion: "Administración → Interacciones",
  para: "Historial de todo contacto con los clientes: pedidos web, correos, llamadas, reuniones y avisos automáticos de la torre de control. Se puede filtrar por canal, categoría o urgencia." }));
contenido.push(...pantalla({ titulo: "7.4 Auditoría", imagenArchivo: "17_admin_auditoria.png", pie: "Registro de eventos: inicios de sesión, fallos, alertas y pedidos",
  direccion: "Administración → Eventos de auditoría",
  para: "Registro de seguridad de quién hizo qué y cuándo: inicios de sesión, intentos fallidos, alertas, cambios en el CRM y pedidos creados.",
  detras: ["Nadie puede modificar ni borrar estos registros, ni siquiera la aplicación: la base de datos solo le permite agregar eventos nuevos.", "Los intentos fallidos se registran sin guardar la contraseña que se intentó."] }));

// ---------- 8. Dashboard ----------
contenido.push(h1("8. Dashboard gerencial (Metabase)"));
contenido.push(...pantalla({ titulo: "8.1 Ventas y canales", imagenArchivo: "metabase-1-ventas.jpg", pie: "Indicadores del mes, ventas semanales por canal y participación B2B/B2C",
  direccion: "https://bi.cofrial-temuco.duckdns.org/dashboard/2", quien: "Gerencia.",
  para: "Reúne en una sola página los números del negocio y de la cadena de frío. Arriba hay cuatro indicadores: ventas de los últimos 30 días, pedidos, camiones fuera de rango en este momento y alertas del mes." }));
contenido.push(...imagen("metabase-2-flota.jpg", "Mapa de la flota y temperatura de cada camión en vivo"));
contenido.push(...imagen("metabase-3-alertas-crm.jpg", "Alertas por día, pedidos afectados y oportunidades por etapa del CRM"));
contenido.push(nota("Qué ve Metabase:", "solo resúmenes preparados para él (vistas del esquema bi). No puede leer nombres, RUT, correos ni contraseñas. Si un gráfico dice Hubo un problema, basta con recargar la página.", TEMPLE));

// ---------- 9. Recorrido completo ----------
contenido.push(h1("9. Un pedido de principio a fin"),
  p("Este recorrido muestra cómo se conectan todas las pantallas. Es el mismo orden que conviene seguir en la demostración."),
  ...[
    ["La compra. ", "La encargada de compras del Hospital Regional entra a la tienda, ve sus precios de convenio y compra 40 kg de pechuga de pollo. El pedido nace como Recibido."],
    ["El CRM se entera solo. ", "En la ficha del hospital aparece el pedido web. La vendedora no tuvo que tomar el pedido por teléfono."],
    ["Preparación y despacho. ", "En Pedidos y catálogo, despacho cambia el estado a En preparación, Asignado y En ruta cuando el camión CF-027 sale de la bodega."],
    ["La falla. ", "En la ruta, el equipo de frío de CF-027 se detiene y la cámara sube a 7,8 °C. Después de dos lecturas fuera de rango, la torre de control abre la alerta."],
    ["Reacción automática. ", "El pedido pasa a En ruta con alerta, el hospital tiene un aviso de urgencia alta en el CRM y la gerencia ve el pedido en Pedidos afectados del dashboard."],
    ["La gestión. ", "El despachador llama al conductor, registra la acción y toma la alerta. Cuando la temperatura vuelve al rango, la alerta se cierra sola."],
    ["La trazabilidad. ", "Todo queda en la auditoría: quién compró, quién cambió los estados y quién atendió la alerta."],
  ].map(([a, c], i, arr) => paso(i === 0 ? L() : listas[listas.length - 1], [b(a), t(c)])));

// ---------- 10. Problemas comunes ----------
contenido.push(h1("10. Problemas comunes"),
  tabla(["Qué pasa", "Por qué", "Qué hacer"], [
    ["Ninguna página carga", "El laboratorio de AWS Academy está apagado", "Iniciar el laboratorio (Start Lab) y esperar unos 10 minutos a que RDS esté disponible"],
    ["Usuario bloqueado al iniciar sesión", "Se equivocó 5 veces seguidas", "Esperar una hora, o que el administrador borre el bloqueo en Administración → Access attempts"],
    ["Perdí el celular con el código de 2FA", "El segundo factor está en ese celular", "El administrador ejecuta python manage.py reiniciar_2fa con el correo de la persona, que luego escanea un QR nuevo"],
    ["Quiero cambiar de celular", "El segundo factor está vinculado al anterior", "Menú lateral → Vincular otro celular"],
    ["Me devuelve a mi sección con un aviso", "La sección no corresponde al rol", "Pedir al administrador que agregue a la persona al grupo correcto"],
    ["El mapa 3D no aparece", "Falta la clave de Mapbox o el navegador no soporta 3D", "La torre muestra el mapa 2D. Revisar la clave MAPBOX_TOKEN en Secrets Manager"],
    ["Un gráfico de Metabase dice Hubo un problema", "Falla de carga del navegador", "Recargar la página"],
    ["La torre dice que no llegan lecturas", "El simulador IoT está detenido", "Revisar el servidor cofrial-iot en EC2"],
    ["Las pruebas dicen que los servidores viejos están encendidos", "AWS Academy enciende todas las máquinas al iniciar el laboratorio", "Detener cofrial-app-server y cofrial-db-server en EC2"],
  ], [2700, 3000, 3938]));

const doc = new Document({
  features: { updateFields: true },
  creator: "Benjamín Aguilar y Daniel Jara", title: "Manual de uso del sistema Cofrial", description: "Manual de usuario",
  styles: {
    default: { document: { run: { font: "Arial", size: 21, color: PIZARRA } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { font: "Arial", size: 60, bold: true, color: PIZARRA }, paragraph: { spacing: { before: 120, after: 200 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Arial", size: 34, bold: true, color: PIZARRA }, paragraph: { spacing: { before: 0, after: 200 }, keepNext: true, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: GLACIAR, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Arial", size: 27, bold: true, color: GLACIAR }, paragraph: { spacing: { before: 320, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: "Arial", size: 22, bold: true, color: PIZARRA }, paragraph: { spacing: { before: 160, after: 60 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "puntos", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...listas.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] })),
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [t("Cofrial SpA, manual de uso", { size: 16, color: NIEBLA })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [t("Página ", { size: 16, color: NIEBLA }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: NIEBLA })] })] }) },
    children: contenido,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("ok", OUT, buf.length); });
