import React, { useEffect, useState } from "react";
import api from "../../services/api";
import CustomDropdown from "../common/CustomDropdown";

export default function GlassFilter({ onFilterChange }) {
  const [brand, setBrand] = useState(null);
  const [type, setType] = useState(null);
  const [subGroup, setSubGroup] = useState(null);
  const [color, setColor] = useState(null);
  const [thickness, setThickness] = useState(null);

  const [options, setOptions] = useState({
    brands: [],
    types: [],
    subGroups: [],
    colors: [],
    thicknesses: [],
  });

  const fetchOptions = async () => {
    try {
      const res = await api.get("/api/items/glass/filter-options", {
        params: { brand, type, subGroup, color, thickness },
      });
      setOptions({
        brands: res.data.brands || [],
        types: res.data.types || [],
        subGroups: res.data.subGroups || [],
        colors: res.data.colors || [],
        thicknesses: res.data.thicknesses || [],
      });
    } catch (err) {
      console.error("Load glass filter options failed:", err);
    }
  };

  useEffect(() => {
    fetchOptions();
  }, []);

  useEffect(() => {
    fetchOptions();
  }, [brand, type, subGroup, color, thickness]);

  useEffect(() => {
    if (onFilterChange) {
      onFilterChange({ brand, type, subGroup, color, thickness });
    }
  }, [brand, type, subGroup, color, thickness]);

  const handleClearAll = () => {
    setBrand(null);
    setType(null);
    setSubGroup(null);
    setColor(null);
    setThickness(null);
  };

  return (
    <div className="flex items-end justify-between p-3 border rounded-xl bg-gray-50">
      <CustomDropdown
        label="Brand"
        value={brand}
        options={options.brands}
        onChange={setBrand}
        width={200}
      />

      <CustomDropdown
        label="Type"
        value={type}
        options={options.types}
        onChange={setType}
        width={160}
      />

      <CustomDropdown
        label="SubGroup"
        value={subGroup}
        options={options.subGroups}
        onChange={setSubGroup}
        width={340}
      />

      <CustomDropdown
        label="Color"
        value={color}
        options={options.colors}
        onChange={setColor}
        width={160}
      />

      <CustomDropdown
        label="Thickness"
        value={thickness}
        options={options.thicknesses}
        onChange={setThickness}
      />

      <button
        onClick={handleClearAll}
        className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-100"
      >
        Clear All
      </button>
    </div>
  );
}
