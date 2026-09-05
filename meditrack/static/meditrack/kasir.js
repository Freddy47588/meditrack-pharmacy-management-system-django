const products = new Map(JSON.parse(document.getElementById('cash-products').textContent).map(product => [String(product.id), product]));
const items = document.getElementById('cash-items');
const money = value => 'Rp ' + value.toLocaleString('id-ID', {minimumFractionDigits: 2, maximumFractionDigits: 2});
function updateEstimate() {
  let total = 0;
  for (const row of items.querySelectorAll('.cash-row')) {
    const product = products.get(row.querySelector('select').value);
    const quantity = Number(row.querySelector('input[type="number"]').value);
    const subtotal = product && quantity > 0 ? Number(product.harga) * quantity : 0;
    total += subtotal;
    row.querySelector('.cash-estimate').textContent = product
      ? money(subtotal) + ' | Stok: ' + product.stok + (quantity > product.stok ? ' (tidak cukup)' : '')
      : 'Pilih obat untuk melihat subtotal.';
  }
  document.getElementById('cash-total').textContent = money(total);
}
items.addEventListener('input', updateEstimate);
items.addEventListener('change', updateEstimate);
document.getElementById('add-row').addEventListener('click', function () {
  const total = document.getElementById('id_form-TOTAL_FORMS');
  items.insertAdjacentHTML('beforeend', document.getElementById('empty-row').innerHTML.replaceAll('__prefix__', total.value));
  total.value = Number(total.value) + 1;
  updateEstimate();
});
updateEstimate();
