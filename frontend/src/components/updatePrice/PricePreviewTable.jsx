export default function PricePreviewTable({ rows }) {
  return (
    <table className="w-full mt-4 border">
      <thead>
        <tr className="grid grid-cols-8 bg-gray-100">
          <th className="col-span-2 text-start">SKU</th>
          <th className="text-start">Branch</th>
          <th>R1 เดิม</th>
          <th>→</th>
          <th>R1 ใหม่</th>
          <th>R2 ใหม่</th>
          <th>Alt Name</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-t grid grid-cols-8">
            <td className="col-span-2 text-sm">{r.sku}</td>
            <td className="text-center text-sm font-mono">{r.BranchCode || r.branch_code || "-"}</td>
            <td className="text-center text-gray-500">{r.old_R1 ?? "-"}</td>
            <td className="text-center">→</td>
            <td className="text-blue-600 text-center">{r.new_R1}</td>
            <td className="text-center">{r.new_R2}</td>
            <td className="text-center">{r.new_alternate_name}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
