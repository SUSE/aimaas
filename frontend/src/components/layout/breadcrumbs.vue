<template>
  <nav aria-label="breadcrumb">
      <ol class="breadcrumb bg-light px-4 py-2 rounded">
        <li class="breadcrumb-item" aria-current="page">
          <i class="eos-icons">home</i>
        </li>
        <slot></slot>
      </ol>
    </nav>
</template>

<script>
export default {
  name: "breadcrumbs",
}
</script>