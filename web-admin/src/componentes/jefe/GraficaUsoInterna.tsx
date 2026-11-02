"use client";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/** Barras de consultas por día. La misma información va en una tabla accesible debajo de la gráfica. */
export default function GraficaUsoInterna({ datos }: { datos: { dia: string; total: number }[] }) {
  return (
    <div role="img" aria-label="Consultas por día" style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={datos} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#c9d4cb" />
          <XAxis dataKey="dia" tickFormatter={(d: string) => d.slice(5)} stroke="#13271e" />
          <YAxis allowDecimals={false} stroke="#13271e" />
          <Tooltip formatter={(v) => [String(v), "Consultas"]} labelFormatter={(l) => `Día ${String(l)}`} />
          <Bar dataKey="total" name="Consultas" fill="#0e7c66" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
