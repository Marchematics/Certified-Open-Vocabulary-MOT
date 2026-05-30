#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
  library(scales)
})

`%||%` <- function(x, y) if (is.null(x)) y else x

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[[1]]) else "scripts/build_figure4_human_audit_density.R"
root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
if (!dir.exists(file.path(root, "data"))) root <- getwd()
data_dir <- file.path(root, "data")
out_dir <- file.path(root, "figures", "figure4_assets", "rebuild")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

read_table <- function(name) {
  read.csv(file.path(data_dir, name), check.names = FALSE, stringsAsFactors = FALSE)
}

pal <- c(
  parc = "#5FA8C9",
  baseline = "#B8C7D9",
  random = "#D7A64A",
  refuse = "#E5705F",
  support = "#76B7B2",
  neutral = "#4A5568",
  dark = "#2F3A4A",
  pale = "#E9EEF3"
)

theme_set(
  theme_classic(base_size = 6.3, base_family = "Arial") +
    theme(
      axis.line = element_line(linewidth = 0.30, colour = "#222222"),
      axis.ticks = element_line(linewidth = 0.30, colour = "#222222"),
      axis.ticks.length = unit(1.7, "pt"),
      axis.text = element_text(size = 5.4, colour = "#222222"),
      axis.title = element_text(size = 5.8, colour = "#222222"),
      panel.grid.major.y = element_line(linewidth = 0.22, colour = "#E8E8E8"),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      strip.background = element_blank(),
      strip.text = element_text(size = 5.9, face = "bold", margin = margin(0.7, 0, 1.2, 0)),
      legend.position = "bottom",
      legend.title = element_blank(),
      legend.text = element_text(size = 5.6),
      plot.title = element_text(size = 6.8, face = "bold", hjust = 0),
      plot.margin = margin(2.2, 2.2, 2.2, 2.2)
    )
)

save_panel <- function(plot, stem, width_mm = 145, height_mm = 47) {
  w <- width_mm / 25.4
  h <- height_mm / 25.4
  pdf_path <- file.path(out_dir, paste0(stem, ".pdf"))
  svg_path <- file.path(out_dir, paste0(stem, ".svg"))
  png_path <- file.path(out_dir, paste0(stem, ".png"))

  grDevices::cairo_pdf(pdf_path, width = w, height = h, family = "Arial")
  print(plot)
  grDevices::dev.off()

  svglite::svglite(svg_path, width = w, height = h, system_fonts = list(sans = "Arial"))
  print(plot)
  grDevices::dev.off()

  if (requireNamespace("pdftools", quietly = TRUE) && requireNamespace("png", quietly = TRUE)) {
    img <- pdftools::pdf_render_page(pdf_path, page = 1, dpi = 320)
    png::writePNG(img, png_path)
  }
  cat("wrote", pdf_path, "\n")
}

long_rows <- function(df, id_cols, value_cols, metric_labels = NULL) {
  pieces <- lapply(value_cols, function(v) {
    z <- df[, c(id_cols, v), drop = FALSE]
    names(z)[ncol(z)] <- "value"
    z$metric <- if (!is.null(metric_labels) && v %in% names(metric_labels)) metric_labels[[v]] else v
    z
  })
  do.call(rbind, pieces)
}

clamp01 <- function(x) pmin(pmax(x, 0), 1)

panel_a_iwildcam_audit_microplots <- function() {
  blocks <- read_table("table_iwildcam_block_coverage.csv")
  counts <- read_table("table_iwildcam_human_confirmed_label_summary.csv")
  labels <- read_table("iwildcam_second_review_human_confirmed_comparison.csv")

  blocks$block_index <- seq_len(nrow(blocks))
  blocks$support_fraction <- ifelse(blocks$candidates > 0, blocks$official_supported / blocks$candidates, NA_real_)
  block_long <- long_rows(
    blocks,
    c("block_index", "location_id"),
    c("candidates", "official_supported", "support_fraction", "max_score", "calibration_audit_candidates"),
    c(
      candidates = "candidates per block",
      official_supported = "official-supported",
      support_fraction = "support fraction",
      max_score = "max detector score",
      calibration_audit_candidates = "audited calibration"
    )
  )
  block_long$metric <- factor(block_long$metric, levels = c(
    "candidates per block", "official-supported", "support fraction",
    "max detector score", "audited calibration"
  ))

  p_blocks <- ggplot(block_long, aes(block_index, value)) +
    geom_point(aes(colour = factor(location_id)), size = 0.62, alpha = 0.75, stroke = 0) +
    geom_smooth(method = "loess", formula = y ~ x, se = FALSE, linewidth = 0.46, colour = unname(pal["dark"]), span = 0.28) +
    facet_wrap(~metric, nrow = 1, scales = "free_y") +
    scale_colour_manual(values = rep(c("#4D7599", "#6EA7A3", "#C39C50", "#A9B7C7", "#7E8BA3"), 100), guide = "none") +
    labs(x = "camera-location block", y = NULL, title = "iWildCam block and audit coverage") +
    theme(axis.text.x = element_blank())

  counts$sample_label <- paste(counts$sample_set_name, counts$human_label, sep = "\n")
  p_counts <- ggplot(counts, aes(sample_label, count, fill = human_label)) +
    geom_col(width = 0.64, linewidth = 0.22, colour = "white") +
    geom_text(aes(label = count), size = 2.1, vjust = -0.25) +
    facet_wrap(~sample_set_name, nrow = 1, scales = "free_x") +
    scale_fill_manual(values = c(animal = unname(pal["parc"]), not_animal = unname(pal["baseline"]))) +
    labs(x = NULL, y = "reviewed rows", title = "human label counts") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1), legend.position = "none")

  labels$score_bin <- cut(labels$score, breaks = seq(0.45, 0.96, by = 0.035), include.lowest = TRUE)
  score_tab <- as.data.frame(table(labels$second_review_stratum, labels$score_bin), stringsAsFactors = FALSE)
  names(score_tab) <- c("stratum", "score_bin", "count")
  score_tab$bin_mid <- as.numeric(sub("^\\((.+),.*", "\\1", gsub("\\[", "(", score_tab$score_bin))) + 0.0175
  score_tab$stratum <- gsub("^all_", "", score_tab$stratum)
  score_tab$stratum <- gsub("_", " ", score_tab$stratum)
  p_scores <- ggplot(score_tab, aes(bin_mid, count)) +
    geom_col(width = 0.03, fill = unname(pal["support"]), colour = "white", linewidth = 0.10) +
    facet_wrap(~stratum, nrow = 1, scales = "free_y") +
    labs(x = "candidate score", y = "rows", title = "blind-review score distributions") +
    coord_cartesian(xlim = c(0.45, 0.96))

  (p_blocks / (p_counts | p_scores)) +
    plot_layout(heights = c(1.02, 0.92), widths = c(0.40, 0.60)) &
    theme(plot.title = element_text(size = 6.0, face = "bold"))
}

panel_b_iwildcam_operating_surface <- function() {
  primary <- read_table("table_iwildcam_human_audit_primary_results.csv")
  random <- read_table("table_iwildcam_random_score_control.csv")

  primary$source <- "PARC audited source"
  random$source <- "random-score control"
  names(random)[names(random) == "mean_official_proxy_FTR"] <- "official_proxy_FTR_mean"
  names(random)[names(random) == "max_official_proxy_FTR"] <- "official_proxy_FTR_max"
  dat <- rbind(
    primary[, c("alpha", "K", "source", "non_empty_seeds", "mean_release", "official_proxy_FTR_mean",
                "mean_raw_topK_official_proxy_FTR", "mean_best_mass_ratio", "max_observed_e", "required_e")],
    random[, c("alpha", "K", "source", "non_empty_seeds", "mean_release", "official_proxy_FTR_mean",
               "mean_raw_topK_official_proxy_FTR", "mean_best_mass_ratio", "max_observed_e", "required_e")]
  )
  dat$seed_fraction <- dat$non_empty_seeds / 20
  dat$release_fraction <- ifelse(dat$K > 0, dat$mean_release / dat$K, 0)
  dat$e_margin <- dat$max_observed_e / dat$required_e
  dat$alpha_label <- paste0("alpha=", dat$alpha)

  long <- long_rows(
    dat,
    c("alpha_label", "K", "source"),
    c("seed_fraction", "release_fraction", "official_proxy_FTR_mean",
      "mean_raw_topK_official_proxy_FTR", "mean_best_mass_ratio", "e_margin"),
    c(
      seed_fraction = "non-empty seed fraction",
      release_fraction = "released/K",
      official_proxy_FTR_mean = "PARC proxy FTR",
      mean_raw_topK_official_proxy_FTR = "raw proxy FTR",
      mean_best_mass_ratio = "mass ratio",
      e_margin = "max e / e req."
    )
  )
  long$metric <- factor(long$metric, levels = c(
    "non-empty seed fraction", "released/K", "PARC proxy FTR",
    "raw proxy FTR", "mass ratio", "max e / e req."
  ))
  ggplot(long, aes(factor(K), value, group = source, colour = source)) +
    geom_hline(data = data.frame(metric = c("mass ratio", "max e / e req."), y = 1),
               aes(yintercept = y), inherit.aes = FALSE, linetype = "dashed", linewidth = 0.30, colour = "#777777") +
    geom_line(linewidth = 0.44, alpha = 0.90) +
    geom_point(size = 1.15) +
    facet_grid(alpha_label ~ metric, scales = "free_y") +
    scale_colour_manual(values = c("PARC audited source" = unname(pal["parc"]), "random-score control" = unname(pal["random"]))) +
    labs(x = "requested K", y = NULL, title = "iWildCam release/refusal operating surface") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1))
}

panel_c_spacenet_audit_surface <- function() {
  seed <- read_table("table_spacenet7_real_audit_seed_results.csv")
  block <- read_table("table_spacenet7_real_audit_block_coverage.csv")

  seed$release_fraction <- ifelse(seed$M > 0, seed$released / seed$M, 0)
  seed$e_margin <- seed$max_observed_e / seed$required_emax
  seed$alpha_label <- paste0("alpha=", seed$alpha)
  seed_long <- long_rows(
    seed,
    c("alpha_label", "seed", "M"),
    c("release_fraction", "best_mass_ratio", "official_GT_FTR",
      "raw_topM_official_GT_FTR", "raw_topM_partial_unsupported_rate", "e_margin"),
    c(
      release_fraction = "released/K",
      best_mass_ratio = "mass ratio",
      official_GT_FTR = "PARC official FTR",
      raw_topM_official_GT_FTR = "raw official FTR",
      raw_topM_partial_unsupported_rate = "raw unsupported",
      e_margin = "max e / e req."
    )
  )
  seed_long$metric <- factor(seed_long$metric, levels = c(
    "released/K", "mass ratio", "PARC official FTR",
    "raw official FTR", "raw unsupported", "max e / e req."
  ))

  p_seed <- ggplot(seed_long, aes(factor(M), value)) +
    geom_hline(data = data.frame(metric = c("mass ratio", "max e / e req."), y = 1),
               aes(yintercept = y), inherit.aes = FALSE, linetype = "dashed", linewidth = 0.30, colour = "#777777") +
    geom_boxplot(width = 0.62, outlier.size = 0.45, linewidth = 0.30, fill = unname(pal["pale"]), colour = unname(pal["dark"])) +
    geom_point(aes(colour = factor(seed %% 5)), position = position_jitter(width = 0.11, height = 0), size = 0.42, alpha = 0.75) +
    facet_grid(alpha_label ~ metric, scales = "free_y") +
    scale_colour_manual(values = rep(c("#5FA8C9", "#76B7B2", "#D7A64A", "#A9B7C7", "#E5705F"), 10), guide = "none") +
    labs(x = "requested K", y = NULL, title = "SpaceNet real-audit seed surface") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1))

  block$block_index <- seq_len(nrow(block))
  block$release_or_raw <- block$n_k50_release_audit_candidates + block$n_raw_topk_audit_candidates
  block_long <- long_rows(
    block,
    c("block_index", "aoi"),
    c("n_calibration_audited", "n_verified_positive", "n_k50_release_audit_candidates",
      "n_raw_topk_audit_candidates", "score_min", "score_max"),
    c(
      n_calibration_audited = "audited/block",
      n_verified_positive = "verified positive",
      n_k50_release_audit_candidates = "K50 release audit",
      n_raw_topk_audit_candidates = "raw top-K audit",
      score_min = "score min",
      score_max = "score max"
    )
  )
  block_long$metric <- factor(block_long$metric, levels = c(
    "audited/block", "verified positive", "K50 release audit",
    "raw top-K audit", "score min", "score max"
  ))
  p_block <- ggplot(block_long, aes(block_index, value)) +
    geom_col(fill = unname(pal["support"]), width = 0.78, alpha = 0.86, linewidth = 0.08, colour = "white") +
    facet_wrap(~metric, nrow = 1, scales = "free_y") +
    labs(x = "AOI-time audit block", y = NULL, title = "SpaceNet audit-block coverage") +
    theme(axis.text.x = element_blank())

  p_seed / p_block + plot_layout(heights = c(1.25, 0.75))
}

panel_d_spacenet_map_consequence_grid <- function() {
  map <- read_table("table_spacenet_map_metric_summary.csv")
  map$source <- ifelse(grepl("random", map$proposal_source), "randomized linker", "geometry linker")
  map$release_fraction <- map$PARC_released_mean / map$K
  map$raw_quality_drop <- 1 - map$raw_persistence_map_quality_proxy_mean
  map$parc_quality_drop <- 1 - map$PARC_persistence_map_quality_proxy_mean
  long <- long_rows(
    map,
    c("source", "K"),
    c("PARC_released_mean", "release_fraction", "raw_false_persistence_links_mean",
      "PARC_false_persistence_links_mean", "prevented_false_persistence_links_mean",
      "raw_map_edit_burden_proxy_mean", "prevented_map_edit_burden_proxy_mean",
      "raw_quality_drop", "parc_quality_drop", "best_mass_ratio_mean"),
    c(
      PARC_released_mean = "PARC released",
      release_fraction = "released/K",
      raw_false_persistence_links_mean = "raw false links",
      PARC_false_persistence_links_mean = "PARC false links",
      prevented_false_persistence_links_mean = "false links prevented",
      raw_map_edit_burden_proxy_mean = "raw map-edit burden",
      prevented_map_edit_burden_proxy_mean = "edit burden prevented",
      raw_quality_drop = "raw quality loss",
      parc_quality_drop = "PARC quality loss",
      best_mass_ratio_mean = "mass ratio"
    )
  )
  long$metric <- factor(long$metric, levels = c(
    "PARC released", "released/K", "raw false links", "PARC false links",
    "false links prevented", "raw map-edit burden", "edit burden prevented",
    "raw quality loss", "PARC quality loss", "mass ratio"
  ))
  ggplot(long, aes(factor(K), value, group = source, colour = source, fill = source)) +
    geom_hline(data = data.frame(metric = "mass ratio", y = 1),
               aes(yintercept = y), inherit.aes = FALSE, linetype = "dashed", linewidth = 0.30, colour = "#777777") +
    geom_col(position = position_dodge(width = 0.72), width = 0.58, alpha = 0.78, colour = "white", linewidth = 0.12) +
    geom_line(position = position_dodge(width = 0.72), linewidth = 0.34) +
    geom_point(position = position_dodge(width = 0.72), size = 0.75) +
    facet_wrap(~metric, nrow = 2, scales = "free_y") +
    scale_colour_manual(values = c("geometry linker" = unname(pal["parc"]), "randomized linker" = unname(pal["refuse"]))) +
    scale_fill_manual(values = c("geometry linker" = unname(pal["parc"]), "randomized linker" = unname(pal["refuse"]))) +
    labs(x = "requested K", y = NULL, title = "SpaceNet downstream map-consequence sweep") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1))
}

main <- function() {
  p_a <- panel_a_iwildcam_audit_microplots()
  p_b <- panel_b_iwildcam_operating_surface()
  p_c <- panel_c_spacenet_audit_surface()
  p_d <- panel_d_spacenet_map_consequence_grid()

  save_panel(p_a, "figure_4a_iwild_audit_microplots", height_mm = 54)
  save_panel(p_b, "figure_4b_iwild_operating_surface", height_mm = 45)
  save_panel(p_c, "figure_4c_spacenet_audit_surface", height_mm = 60)
  save_panel(p_d, "figure_4d_spacenet_map_consequence_grid", height_mm = 50)
}

main()
