import { allure } from 'allure-playwright'

type FrontendLayer = 'base' | 'middle' | 'top'

export async function applyFrontendE2EAllureLabels(
  suiteName: string,
  layerName: FrontendLayer = 'top',
) {
  await allure.parentSuite('Frontend')
  await allure.suite(suiteName)
  await allure.layer(layerName)
  await allure.tags(`layer:${layerName}`)
}
