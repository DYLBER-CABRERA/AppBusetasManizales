import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Bricolage_Grotesque } from "next/font/google";
import { Proveedores } from "@/componentes/Proveedores";
import "@/estilos/globales.css";

const titulo = Bricolage_Grotesque({ subsets: ["latin"], variable: "--fuente-titulo" });
const texto = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--fuente-texto" });

export const metadata: Metadata = {
  title: "BusetasApp · Paneles de gestión",
  description: "Paneles de escritorio de BusetasApp Manizales (datos de ejemplo).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${titulo.variable} ${texto.variable}`}>
      <body className="min-w-[1024px] antialiased">
        <Proveedores>{children}</Proveedores>
      </body>
    </html>
  );
}
