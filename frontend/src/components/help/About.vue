<template>
  <h1>Abstract Information Management and Authority Service</h1>
  <p>
    <em>aimaas</em> is a web application for information management with a focus on dynamic data
    structures and change management.
  </p>
  <div class="row mt-5">
    <div class="col-lg-4">
      <h3><i class="eos-icons me-2">namespace</i>Dynamic data structures</h3>
    </div>
    <div class="col-lg-8">
      <p>
        The primary intention of <em>aimaas</em> is to enable users to define table-like data
        structures without the hassle of dealing with a database.
      </p>
      <p>
        In <em>aimaas</em> we call those structures <b>schemas</b>. The data sets contained in
        these schemas are referred to as <b>entities</b>.
      </p>
      <div class="gap-3 d-md-flex d-grid">
        <router-link :to="{name: 'schema-list'}" class="btn btn-cta flex-fill">
          <i class="eos-icons me-2">explore</i> Explore existing schemas
        </router-link>
        <router-link :to="{name: 'schema-new'}" class="btn btn-cta flex-fill">
          <i class="eos-icons me-2">add_circle</i> Create a new schema
        </router-link>
      </div>
    </div>
  </div>
  <div class="row mt-5">
    <div class="col-lg-4">
      <h3><i class="eos-icons me-2">thumbs_up_down</i>Change Management</h3>
    </div>
    <div class="col-lg-8">
      <p>
        An important part of managing information is to keep track of changes. For this purpose,
        <em>aimaas</em> not only keeps a detailed log of changes applied to entities, but also
        allows to enable a review system.
      </p>
      <p>
        The review system allows users to propose changes and review them. During this process other
        clients will receive the unchanged information; until the changes are approved.
      </p>
    </div>
  </div>
  <div class="row mt-5">
    <div class="col-lg-4">
      <h3><i class="eos-icons me-2">groups</i>Permission Management</h3>
    </div>
    <div class="col-lg-8">
      <p>
        <em>aimaas</em> does not allow anybody to do anything. Users need <b>permissions</b> for
        actions.
      </p>
      <p>
        Permissions can be granted to users or groups of users on a schema level (applicable to all
        entities in the schema) and even the entity level.
      </p>
    </div>
  </div>
  <div class="row mt-5">
    <div class="col-lg-4">
      <h3><i class="eos-icons me-2">network</i> Further resources</h3>
    </div>
    <div class="col-lg-8">
      <div class="d-flex justify-content-between">
        <a :href="`mailto:${apiInfo?.help.email}`" v-if="apiInfo?.help.email">
          <i class="eos-icons me-1">email</i> Mail
        </a>
        <a :href="apiInfo?.help.chat_url" v-if="apiInfo?.help.chat_url">
          <i class="eos-icons me-1">chat</i> Chat
        </a>
        <a :href="apiInfo?.help.tracker_url">
          <i class="eos-icons me-1">bug_report</i> Report issues
        </a>
        <a :href="apiInfo?.help.source_url"><i class="eos-icons me-1">source</i> Source code</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "About",
  inject: ["apiInfo"]
}
</script>

<style scoped>

</style>
