#!/usr/bin/env Rscript

# Current main Figure 2 density rebuild.
#
# Contract:
# - Backend: R only.
# - Claim: release/refusal changes downstream scientific artifacts.
# - Layout: four large LaTeX-assembled panels.
# - Every internal unit is a data visualization: no text-card panels and no
#   status-only matrices.

required_packages <- c("ggplot2", "patchwork", "svglite")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop(
    paste0(
      "Missing required R packages: ",
      paste(missing_packages, collapse = ", "),
      ". Install with install.packages(c(",
      paste(sprintf('\"%s\"', missing_packages), collapse = ", "),
      "))."
    ),
    call. = FALSE
  )
}

library(ggplot2)
library(patchwork)

args <- commandArgs(FALSE)
script_file <- sub("^--file=", "", args[grep("^--file=", args)[1]])
if (is.na(script_file) || !nzchar(script_file)) {
  script_file <- "scripts/build_figure6_consequence_density.R"
}
root <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
data_dir <- file.path(root, "data")
out_dir <- file.path(root, "figures", "figure6_assets", "rebuild")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pal <- c(
  ink = "#272727",
  grid = "#E6E6E6",
  raw = "#8F8F8F",
  topR = "#577399",
  parc = "#5EA6C8",
  prevented = "#76B7B2",
  refusal = "#D96B5F",
  boundary = "#D6A55D",
  support = "#9BC491",
  neutral = "#D7D7D7",
  purple = "#7C6A9E"
)

theme_parc_nmi <- function(base_size = 6.1, base_family = "Arial") {
  theme_classic(base_size = base_size, base_family = base_family) +
    theme(
      axis.line = element_line(linewidth = 0.28, colour = pal[["ink"]]),
      axis.ticks = element_line(linewidth = 0.28, colour = pal[["ink"]]),
      axis.title = element_text(size = base_size),
      axis.text = element_text(size = base_size - 0.7, colour = pal[["ink"]]),
      legend.title = element_text(size = base_size - 0.35),
      legend.text = element_text(size = base_size - 0.8),
      legend.key.size = unit(0.22, "cm"),
      strip.background = element_rect(fill = "#F2F4F5", colour = NA),
      strip.text = element_text(size = base_size - 0.35, face = "bold"),
      plot.title = element_text(size = base_size + 0.35, face = "bold", hjust = 0),
      plot.margin = margin(2, 3, 2, 3, "pt"),
      panel.grid.major.y = element_line(linewidth = 0.18, colour = pal[["grid"]]),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank()
    )
}
theme_set(theme_parc_nmi())

save_panel <- function(plot, stem, width_mm = 91, height_mm = 62, dpi = 600) {
  base <- file.path(out_dir, stem)
  w <- width_mm / 25.4
  h <- height_mm / 25.4

  svglite::svglite(paste0(base, ".svg"), width = w, height = h)
  print(plot)
  invisible(dev.off())

  grDevices::cairo_pdf(paste0(base, ".pdf"), width = w, height = h, family = "Arial")
  print(plot)
  invisible(dev.off())

  grDevices::png(paste0(base, ".png"), width = w, height = h, units = "in", res = dpi, type = "cairo")
  print(plot)
  invisible(dev.off())

  message("wrote ", file.path("figures", "figure6_assets", "rebuild", paste0(stem, ".pdf")))
}

read_required <- function(path) {
  full <- file.path(data_dir, path)
  if (!file.exists(full)) {
    stop("Required data file missing: ", full, call. = FALSE)
  }
  read.csv(full, stringsAsFactors = FALSE)
}

pretty_model <- function(x) {
  x <- gsub("CGCNN 10-member ensemble", "CGCNN", x)
  x <- gsub("ALIGNN-FF", "ALIGNN", x)
  x <- gsub("MEGNet", "MEGNet", x)
  x
}

rescale01 <- function(x) {
  rng <- range(x, na.rm = TRUE)
  if (!is.finite(rng[1]) || diff(rng) == 0) {
    return(rep(0, length(x)))
  }
  (x - rng[1]) / diff(rng)
}

materials_summary <- read_required("table_fixed_budget_primary.csv")
materials_seed <- read_required("table_fixed_budget_seed_rows.csv")
ctc_summary <- read_required("table_ctc_official_lineage_metric_summary.csv")
spacenet_summary <- read_required("table_spacenet_map_metric_summary.csv")
release_cards <- read_required("figure_release_certification_benchmark_map.csv")

materials_summary <- subset(materials_summary, rho == 0.1 & alpha == 0.1)
materials_seed <- subset(materials_seed, rho == 0.1 & alpha == 0.1)

# Panel a: materials follow-up queue as real seed distributions and K-sweeps.
mat_seed_focus <- subset(materials_seed, model_family == "ALIGNN-FF" & K %in% c(300, 500))
mat_seed_long <- rbind(
  data.frame(K = mat_seed_focus$K, seed = mat_seed_focus$seed, metric = "raw", value = mat_seed_focus$raw_unstable_count),
  data.frame(K = mat_seed_focus$K, seed = mat_seed_focus$seed, metric = "PARC", value = mat_seed_focus$PARC_unstable_count),
  data.frame(K = mat_seed_focus$K, seed = mat_seed_focus$seed, metric = "prevented", value = mat_seed_focus$prevented_unstable_followups),
  data.frame(K = mat_seed_focus$K, seed = mat_seed_focus$seed, metric = "released", value = mat_seed_focus$released)
)
mat_seed_long$metric <- factor(mat_seed_long$metric, levels = c("raw", "PARC", "prevented", "released"))
mat_seed_long$K <- factor(paste0("K=", mat_seed_long$K), levels = c("K=300", "K=500"))

p_a1 <- ggplot(mat_seed_long, aes(x = factor(seed), y = value, fill = metric)) +
  geom_col(width = 0.78, colour = "white", linewidth = 0.05, show.legend = FALSE) +
  facet_grid(metric ~ K, scales = "free_y") +
  scale_fill_manual(values = c("raw" = pal[["raw"]], "PARC" = pal[["parc"]],
    "prevented" = pal[["prevented"]], "released" = pal[["topR"]])) +
  labs(x = "seed", y = "count / seed", title = "ALIGNN follow-up objects") +
  theme(
    axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    strip.text = element_text(size = 5.0, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.3, face = "bold")
  )

mat_front <- subset(materials_summary, K %in% c(100, 300, 500, 1000, 5000))
mat_front$model <- factor(pretty_model(mat_front$model_family), levels = c("CGCNN", "ALIGNN", "MEGNet"))
mat_front_long <- rbind(
  data.frame(model = mat_front$model, K = mat_front$K, metric = "raw FTR", value = mat_front$raw_topK_FTR_mean),
  data.frame(model = mat_front$model, K = mat_front$K, metric = "PARC FTR", value = mat_front$PARC_FTR_mean),
  data.frame(model = mat_front$model, K = mat_front$K, metric = "nonempty", value = mat_front$non_empty_seeds / mat_front$seeds),
  data.frame(model = mat_front$model, K = mat_front$K, metric = "prevented", value = mat_front$prevented_unstable_followups_mean)
)
mat_front_long$metric <- factor(mat_front_long$metric, levels = c("raw FTR", "PARC FTR", "nonempty", "prevented"))

p_a2 <- ggplot(mat_front_long, aes(x = K, y = value, colour = model, group = model)) +
  geom_line(linewidth = 0.42) +
  geom_point(size = 0.9) +
  facet_wrap(~metric, nrow = 1, scales = "free_y") +
  scale_x_continuous(trans = "log10", breaks = c(100, 5000), labels = c("100", "5k")) +
  scale_colour_manual(values = c("CGCNN" = pal[["purple"]], "ALIGNN" = pal[["parc"]], "MEGNet" = pal[["support"]])) +
  labs(x = "requested K", y = NULL, colour = NULL, title = "Public-label model/budget frontier") +
  theme(
    legend.position = "bottom",
    legend.margin = margin(-5, 0, -5, 0, "pt"),
    strip.text = element_text(size = 5.2, face = "bold"),
    axis.text.x = element_text(size = 4.7)
  )

p_a <- p_a1 / p_a2 + plot_layout(heights = c(1.25, 0.85))
save_panel(p_a, "figure_6a_materials_artifact_grid", 91, 68)

# Panel b: CTC official-GT consequence across K and source.
ctc_summary$source <- factor(
  ctc_summary$proposal_source,
  levels = c("ctc_learned_hybrid", "ctc_noisy_geometric_linker", "ctc_random_score_negative_control"),
  labels = c("learned", "noisy", "random")
)
ctc_long <- rbind(
  data.frame(source = ctc_summary$source, K = ctc_summary$K, metric = "false edges", value = ctc_summary$raw_false_lineage_edges_mean),
  data.frame(source = ctc_summary$source, K = ctc_summary$K, metric = "prevented", value = ctc_summary$prevented_false_lineage_edges_mean),
  data.frame(source = ctc_summary$source, K = ctc_summary$K, metric = "components", value = ctc_summary$raw_corrupted_lineage_components_mean),
  data.frame(source = ctc_summary$source, K = ctc_summary$K, metric = "false frac.", value = ctc_summary$raw_false_edge_fraction_mean),
  data.frame(source = ctc_summary$source, K = ctc_summary$K, metric = "release frac.", value = ctc_summary$non_empty_seeds / ctc_summary$seeds),
  data.frame(source = ctc_summary$source, K = ctc_summary$K, metric = "mass", value = ctc_summary$best_mass_ratio_mean)
)
ctc_long <- subset(ctc_long, !is.na(source))
ctc_long$metric <- factor(ctc_long$metric, levels = c(
  "false edges", "prevented", "components",
  "false frac.", "release frac.", "mass"
))

p_b <- ggplot(ctc_long, aes(x = K, y = value, colour = source, group = source)) +
  geom_hline(data = data.frame(metric = factor("mass", levels = levels(ctc_long$metric)), value = 1),
    aes(yintercept = value), inherit.aes = FALSE, linewidth = 0.25, linetype = "dashed", colour = "#B55B53") +
  geom_line(linewidth = 0.42) +
  geom_point(size = 0.85) +
  facet_grid(metric ~ source, scales = "free_y") +
  scale_x_continuous(trans = "log10", breaks = c(100, 300, 500, 1000, 5000), labels = c("100", "300", "500", "1k", "5k")) +
  scale_colour_manual(values = c("learned" = pal[["parc"]], "noisy" = pal[["boundary"]], "random" = pal[["refusal"]])) +
  labs(x = "requested K", y = NULL, colour = NULL, title = "CTC lineage artifact metrics") +
  theme(
    legend.position = "none",
    strip.text = element_text(size = 4.7, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.2, face = "bold"),
    axis.text.x = element_text(size = 4.7, angle = 25, hjust = 1),
    axis.text.y = element_text(size = 4.9)
  )
save_panel(p_b, "figure_6b_ctc_artifact_grid", 91, 68)

# Panel c: SpaceNet official-ID consequence across K and source.
spacenet_summary$source <- factor(
  spacenet_summary$proposal_source,
  levels = c("spacenet_geometry_linker", "spacenet_identity_preserving_random_score_control"),
  labels = c("geometry", "random")
)
space_long <- rbind(
  data.frame(source = spacenet_summary$source, K = spacenet_summary$K, metric = "false links", value = spacenet_summary$raw_false_persistence_links_mean),
  data.frame(source = spacenet_summary$source, K = spacenet_summary$K, metric = "prevented", value = spacenet_summary$prevented_false_persistence_links_mean),
  data.frame(source = spacenet_summary$source, K = spacenet_summary$K, metric = "chains", value = spacenet_summary$raw_false_persistence_chains_mean),
  data.frame(source = spacenet_summary$source, K = spacenet_summary$K, metric = "edit proxy", value = spacenet_summary$raw_map_edit_burden_proxy_mean),
  data.frame(source = spacenet_summary$source, K = spacenet_summary$K, metric = "false frac.", value = spacenet_summary$raw_false_link_fraction_mean),
  data.frame(source = spacenet_summary$source, K = spacenet_summary$K, metric = "release frac.", value = spacenet_summary$non_empty_seeds / spacenet_summary$seeds)
)
space_long <- subset(space_long, !is.na(source))
space_long$metric <- factor(space_long$metric, levels = c(
  "false links", "prevented", "chains",
  "edit proxy", "false frac.", "release frac."
))

p_c <- ggplot(space_long, aes(x = K, y = value, colour = source, group = source)) +
  geom_line(linewidth = 0.42) +
  geom_point(size = 0.85) +
  facet_grid(metric ~ source, scales = "free_y") +
  scale_x_continuous(trans = "log10", breaks = c(100, 300, 500, 1000, 5000), labels = c("100", "300", "500", "1k", "5k")) +
  scale_colour_manual(values = c("geometry" = pal[["parc"]], "random" = pal[["refusal"]])) +
  labs(x = "requested K", y = NULL, colour = NULL, title = "SpaceNet persistence-map metrics") +
  theme(
    legend.position = "none",
    strip.text = element_text(size = 4.7, face = "bold"),
    strip.text.y = element_text(angle = 0, size = 4.2, face = "bold"),
    axis.text.x = element_text(size = 4.7, angle = 25, hjust = 1),
    axis.text.y = element_text(size = 4.9)
  )
save_panel(p_c, "figure_6c_map_audit_grid", 91, 68)

# Panel d: release-card quantitative map, not a claim/status matrix.
cards <- release_cards
cards$card_short <- cards$card_id
cards$card_short <- gsub("materials_alignn_followup_alpha010_", "mat ", cards$card_short)
cards$card_short <- gsub("ctc_random_score_negative_control_official_lineage_refusal_", "CTC rand ", cards$card_short)
cards$card_short <- gsub("ctc_noisy_geometric_linker_official_lineage_refusal_", "CTC noisy ", cards$card_short)
cards$card_short <- gsub("ctc_learned_strict_alpha010_", "CTC ", cards$card_short)
cards$card_short <- gsub("ctc_strict_human_confirmed_release_queue", "CTC audit", cards$card_short)
cards$card_short <- gsub("iwildcam_animal_human_audit_alpha020_", "iWild ", cards$card_short)
cards$card_short <- gsub("spacenet_identity_preserving_random_score_control_official_map_", "SN rand ", cards$card_short)
cards$card_short <- gsub("spacenet_geometry_linker_official_map_", "SN geom ", cards$card_short)
cards$card_short <- gsub("_", " ", cards$card_short)
cards$domain_short <- factor(cards$domain,
  levels = c("biomedical_cell_tracking", "materials_discovery", "ecological_camera_traps", "earth_observation"),
  labels = c("CTC", "materials", "iWildCam", "SpaceNet")
)
cards$decision_group <- ifelse(grepl("refusal", cards$PARC_decision), "refusal",
  ifelse(grepl("human", cards$PARC_decision), "audit release", "certified release")
)

card_long <- rbind(
  data.frame(card = cards$card_short, domain = cards$domain_short, decision = cards$decision_group, metric = "mean release", value = cards$mean_release),
  data.frame(card = cards$card_short, domain = cards$domain_short, decision = cards$decision_group, metric = "raw FTR", value = cards$raw_topK_FTR),
  data.frame(card = cards$card_short, domain = cards$domain_short, decision = cards$decision_group, metric = "PARC FTR", value = cards$PARC_FTR),
  data.frame(card = cards$card_short, domain = cards$domain_short, decision = cards$decision_group, metric = "nonempty seeds", value = cards$non_empty_seeds / cards$seeds),
  data.frame(card = cards$card_short, domain = cards$domain_short, decision = cards$decision_group, metric = "rel./prevented", value = cards$release_or_prevented_value)
)
card_long$metric <- factor(card_long$metric, levels = c("mean release", "rel./prevented", "raw FTR", "PARC FTR", "nonempty seeds"))
card_order <- unique(cards$card_short[order(cards$domain_short, cards$requested_K)])
card_long$card <- factor(card_long$card, levels = rev(card_order))
card_long$scaled <- ave(card_long$value, card_long$metric, FUN = rescale01)

p_d <- ggplot(card_long, aes(x = scaled, y = card, fill = decision)) +
  geom_col(width = 0.66, colour = "white", linewidth = 0.08) +
  geom_point(aes(x = pmin(scaled + 0.015, 1.02)), shape = 21, size = 0.7, stroke = 0.15, fill = "white", colour = pal[["ink"]]) +
  facet_wrap(~metric, nrow = 1, scales = "free_x") +
  scale_fill_manual(values = c("certified release" = pal[["parc"]], "audit release" = pal[["support"]], refusal = pal[["refusal"]])) +
  scale_x_continuous(limits = c(0, 1.04), breaks = c(0, 0.5, 1), labels = c("low", "", "high")) +
  labs(x = "within-metric scale", y = NULL, fill = NULL, title = "Release-card quantitative map") +
  theme(
    legend.position = "bottom",
    legend.justification = "left",
    legend.margin = margin(1, 0, 1, 0, "pt"),
    legend.box.margin = margin(1, 0, 1, 0, "pt"),
    strip.text = element_text(size = 5.2, face = "bold"),
    axis.text.y = element_text(size = 4.8),
    panel.grid.major.x = element_line(linewidth = 0.18, colour = pal[["grid"]]),
    panel.grid.major.y = element_blank(),
    plot.margin = margin(3, 4, 6, 4, "pt")
  )
save_panel(p_d, "figure_6d_release_card_quant_grid", 91, 74)

message("Done. Four quantitative dense panel PDFs are ready for LaTeX assembly.")
