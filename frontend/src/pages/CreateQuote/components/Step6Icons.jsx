import React from "react";

export const FileIcon = () => (
  <img src="/assets/folder.png" alt="Print" className="h-6 w-6 mr-2 object-contain" />
);

export const SaveIcon = () => (
  <img src="/assets/Save.png" alt="Print" className="h-5 w-5 mr-2 object-contain" />
);

export const DraftIcon = () => (
  <img src="/assets/draft.png" alt="Print" className="h-6 w-6 mr-2 object-contain" />
);

export const PrintIcon = () => (
  <img src="/assets/printer.png" alt="Print" className="h-5 w-5 mr-2 object-contain" />
);

export const ArrowLeftIcon = () => (
  <svg
    className="w-5 h-5 mr-2"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={2}
    stroke="currentColor"
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
  </svg>
);
