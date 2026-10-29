export default function Excel() {
  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">Cargar rodamiento desde Excel</h1>
      <div className="rounded-lg border border-borde bg-white p-6">
        <p className="mb-4">La carga de archivos Excel no está disponible en esta versión.</p>
        <button type="button" disabled aria-disabled="true"
          className="min-h-11 cursor-not-allowed rounded bg-borde px-4 font-semibold text-tinta">
          Subir archivo
        </button>
        <p className="mt-2 text-sm">No incluido en el prototipo.</p>
      </div>
    </section>
  );
}
