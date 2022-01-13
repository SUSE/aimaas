<template>
  <div class="d-md-flex align-items-center mt-1 gap-2">
    <div class="my-1 me-auto">
      <nav>
        <ul class="pagination mb-0">
          <li class="page-item" :class="modelValue > 1? '': 'disabled'">
            <a class="page-link" v-on:click="tryGoPrevious">
              <span>&laquo;</span>
            </a>
          </li>
          <li class="page-item" v-for="page of this.pages" :key="page.value"
              :class="page.class">
            <a class="page-link" v-on:click="onUpdate(page.value)">{{ page.value }}</a>
          </li>
          <li class="page-item"  :class="modelValue < pageCount? '': 'disabled'">
            <a class="page-link" v-on:click="tryGoNext">
              <span>&raquo;</span>
            </a>
          </li>
        </ul>
      </nav>
    </div>
    <div class="d-flex gap-2">
      <label for="entitiesLimit" class="me-1"><small>Page size</small></label>
      <div>
        <select v-model="pageSize" id="entitiesLimit" class="form-select form-select-sm"
                style="width: 5.5rem;" @change="$emit('change')">
          <option>2</option>
          <option>10</option>
          <option>30</option>
          <option>50</option>
        </select>
      </div>
    </div>
    <small>{{ totalItems }} result(s)</small>
  </div>
  <slot>
    <div class="alert alert-warning">
      You need to display your page here.
    </div>
  </slot>
</template>

<script>
import {range} from "lodash";

export default {
  name: "Pagination",
  props: {
    modelValue: {
      required: true,
      type: Number
    },
    totalItems: {
      type: Number,
      required: true
    },
  },
  data() {
    return {
      pageSize: 10,
      navWidth: 8  // Only use even numbers for navWidth!
    }
  },
  emits: ["update:modelValue", "change"],
  computed: {
    pageCount() {
      return Math.ceil(this.totalItems / this.pageSize);
    },
    pages() {
      if (this.pageCount > this.navWidth) {
        const placeholder = {value: "...", class: 'disabled'};
        const halfNavWidth = Math.floor(this.navWidth / 2);
        const myRange = [];
        let lowerBound, upperBound;
        if (this.modelValue < halfNavWidth) {
          lowerBound = 1;
          upperBound = Math.min(this.navWidth + lowerBound - 1, this.pageCount + 1);
        }
        else if (this.modelValue > this.pageCount - halfNavWidth) {
          upperBound =  this.pageCount + 1;
          lowerBound = Math.max(upperBound - this.navWidth + 1, 1);
        }
        else {
          lowerBound = Math.max(this.modelValue - halfNavWidth + 2, 1);
          upperBound = Math.min(this.modelValue + halfNavWidth, this.pageCount + 1);
        }

        if (lowerBound > 1) {
          myRange.push(placeholder);
        }
        for (const i of range(lowerBound, upperBound)) {
          myRange.push({value: i, class: i === this.modelValue ? 'active' : ''});
        }
        if (upperBound <= this.pageCount) {
          myRange.push(placeholder);
        }
        return myRange;
      } else {
        return range(1, this.pageCount + 1).map(i => {
          return {value: i, class: i === this.modelValue ? 'active' : ''};
        });
      }
    }
  },
  methods: {
    onUpdate(newValue){
      this.$emit('update:modelValue', newValue);
    },
    tryGoPrevious() {
      if (this.modelValue > 1)
        this.onUpdate(this.modelValue - 1);
    },
    tryGoNext() {
      if (this.modelValue < this.pageCount)
        this.onUpdate(this.modelValue + 1);
    }
  }
};
</script>
