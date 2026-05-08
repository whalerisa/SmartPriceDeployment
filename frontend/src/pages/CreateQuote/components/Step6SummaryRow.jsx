import React from "react";

export const SummaryRow = ({ label, value, isTotal = false, loading = false }) => (
  <div className="flex justify-between py-2">
    <span className={`font-semibold ${isTotal ? "text-lg text-gray-900" : "text-gray-600"}`}>
      {label}
    </span>
    <span className={`font-bold ${isTotal ? "text-xl text-blue-600" : "text-gray-800"}`}>
      {loading ? (
        <span className="inline-block h-4 w-24 animate-pulse rounded-md bg-gray-300" />
      ) : (
        value
      )}
    </span>
  </div>
);
