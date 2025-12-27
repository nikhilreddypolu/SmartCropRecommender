// ===== Simple-DataTables (no jQuery) =====
(function () {
  const tables = document.querySelectorAll("table.datatable");
  tables.forEach((t) => {
    try {
      const DataTable = window.simpleDatatables?.DataTable || window.DataTable;
      if (DataTable) {
        new DataTable(t, {
          searchable: true,
          fixedHeight: false,
          perPage: 10,
          perPageSelect: [10, 25, 50, 100]
        });
      }
    } catch (e) {
      console.warn("DataTable init error:", e);
    }
  });
})();

// ===== SweetAlert2 confirm for delete forms =====
(function () {
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-confirm='delete']");
    if (!btn) return;

    e.preventDefault();
    const form = btn.closest("form");
    if (!form) return;

    Swal.fire({
      icon: "warning",
      title: "Are you sure?",
      text: "This action cannot be undone.",
      showCancelButton: true,
      confirmButtonText: "Yes, delete it",
    }).then((res) => {
      if (res.isConfirmed) form.submit();
    });
  });
})();
