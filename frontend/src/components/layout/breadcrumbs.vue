<template>
  <nav aria-label="breadcrumb">
      <ol class="breadcrumb bg-light px-4 py-2 rounded">
        <li class="breadcrumb-item" aria-current="page">
          <RouterLink class="navbar-brand" :to="{name: 'schema-list'}">
            <i class="eos-icons">home</i>
          </RouterLink>
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