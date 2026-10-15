document.addEventListener("DOMContentLoaded", () => {
  const calculator = document.querySelector("#business-case-calculator");
  if (!calculator) return;

  const input = (name) => Number(calculator.querySelector(`[data-input="${name}"]`).value) || 0;
  const output = (name, value) => {
    calculator.closest("section").querySelector(`[data-output="${name}"]`).textContent = value;
  };
  const format = (value) =>
    `${value > 0 ? "+" : ""}${Number.isInteger(value) ? value : value.toFixed(1)}`;

  const calculate = () => {
    const spend = input("S");
    const transition = input("B");
    const recurring = input("R");
    const years = Math.max(1, input("years"));
    const loadedCost = Math.max(1, input("loadedCost"));
    const nonLabor = input("nonLabor");
    const net = years * spend - transition - years * recurring;
    const payback = spend > recurring
      ? `${((transition / (spend - recurring)) * 12).toFixed(1)}`
      : "No payback";
    const breakEven = spend - transition / years;
    const capacity = (spend - nonLabor - transition / years) / loadedCost;

    output("net", format(net));
    output("payback", payback);
    output("breakEven", format(breakEven));
    output("capacity", capacity.toFixed(2));
  };

  calculator.addEventListener("input", calculate);
  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      const [spend, transition, recurring] = button.dataset.preset.split(",");
      calculator.querySelector('[data-input="S"]').value = spend;
      calculator.querySelector('[data-input="B"]').value = transition;
      calculator.querySelector('[data-input="R"]').value = recurring;
      calculate();
    });
  });
  calculate();
});
