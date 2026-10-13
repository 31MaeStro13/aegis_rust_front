use pyo3::prelude::*;

/// Точка входа для Python-модуля aegis_core.
/// Спецификация функций и требования описаны в docs/RUST_CORE_SPEC.md.
#[pymodule]
fn aegis_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Регистрация функций будет добавлена при реализации
    Ok(())
}
