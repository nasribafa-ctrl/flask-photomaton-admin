// POSITIVE
const selectPositive = document.getElementById("selectionpositive");
const textareaPositive = document.getElementById("textareapositive");

if (selectPositive && textareaPositive) {
    selectPositive.addEventListener("change", function () {
        textareaPositive.value = this.value;
    });
}

// NEGATIVE
const selectNegative = document.getElementById("selectionnegative");
const textareaNegative = document.getElementById("textareanegative");

if (selectNegative && textareaNegative) {
    selectNegative.addEventListener("change", function () {
        textareaNegative.value = this.value;
    });
}
